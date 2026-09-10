"""Interactive Lean backend (spec section 14).

Persistent Lean REPL process per session. Minimal interface:

    create_session() load_environment() submit_action(action)
    get_proof_state() get_errors() reset() close()

Each action returns: previous_state, action, next_state, errors,
execution_time, status (section 14).

Failure attribution (section 64): a Lean process crash is
LEAN_FAILURE / INFRASTRUCTURE_FAILURE, never a mathematical FAIL.
Interactive SUCCESS never replaces batch verification (section 13).
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import Config
from ..lean_env import LeanEnvironment, source_hash
from .statuses import Diagnostic, FailureClass, ProofStatus


class BackendCrash(RuntimeError):
    """The Lean REPL process died - infrastructure event, not a math failure."""

    def __init__(self, message: str, failure_class: FailureClass = FailureClass.LEAN_FAILURE):
        super().__init__(message)
        self.failure_class = failure_class


@dataclass
class ProofState:
    """Minimal normalized proof state (section 32 baseline).

    Raw Lean structures are never passed to the model; the original Lean
    representation stays with the verifier.
    """

    status: str
    errors: list[Diagnostic] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    declaration_count: int = 0
    raw_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": [e.to_dict() for e in self.errors],
            "infos": list(self.infos),
            "declaration_count": self.declaration_count,
            "raw_summary": self.raw_summary,
        }


@dataclass
class ActionResult:
    """One interactive action record (section 14)."""

    previous_state: ProofState
    action: str
    next_state: ProofState
    errors: list[Diagnostic]
    execution_time: float
    status: ProofStatus
    failure_class: FailureClass | None = None
    source_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_state": self.previous_state.to_dict(),
            "action": self.action,
            "next_state": self.next_state.to_dict(),
            "errors": [e.to_dict() for e in self.errors],
            "execution_time": round(self.execution_time, 6),
            "status": self.status.value,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "source_hash": self.source_hash,
        }


def _parse_serialized_message(m: dict) -> Diagnostic:
    severity = {"error": "error", "warning": "warning", "information": "info"}.get(
        str(m.get("severity", "error")), "error"
    )
    pos = m.get("pos") or {}
    return Diagnostic(
        severity=severity,
        line=int(pos.get("line", 0)) or None,
        column=int(pos.get("column", 0)) or None,
        message=str(m.get("data", "")),
        raw=json.dumps(m, ensure_ascii=False),
    )


_IMPORT_LINE_PREFIXES = ("import ",)


def _strip_imports(source: str) -> str:
    """Remove import lines (session environment is fixed at spawn, s11)."""
    kept = [
        line for line in source.splitlines()
        if not line.lstrip().startswith(_IMPORT_LINE_PREFIXES)
    ]
    return "\n".join(kept)


class InteractiveSession:
    """One persistent Lean REPL process (section 14)."""

    def __init__(self, config: Config, environment: LeanEnvironment,
                 imports: tuple[str, ...] = ("Mathesis.Basic",)):
        self._cfg = config
        self._env_meta = environment
        self._imports = imports
        self._package_dir = Path(config.lean.package_dir).resolve()
        self._elan_home = Path(config.lean.elan_home).resolve()
        self._exe = self._package_dir / ".lake" / "build" / "bin" / "mathesis_repl.exe"
        self._proc: subprocess.Popen | None = None
        self._queue: queue.Queue = queue.Queue()
        self._reader: threading.Thread | None = None
        self._state = ProofState(status="fresh")
        self._closed = False
        self.create_session()

    # ------------------------------------------------------------------ #
    # process lifecycle
    # ------------------------------------------------------------------ #

    def _process_env(self) -> dict:
        env = os.environ.copy()
        env["ELAN_HOME"] = str(self._elan_home)
        toolchain_dir = self._resolve_toolchain_dir()
        if toolchain_dir is not None:
            env["LEAN_SYSROOT"] = str(toolchain_dir)
        return env

    def _resolve_toolchain_dir(self) -> Path | None:
        tc_root = self._elan_home / "toolchains"
        if not tc_root.exists():
            return None
        dirs = sorted(p for p in tc_root.iterdir() if p.is_dir())
        if len(dirs) == 1:
            return dirs[0]
        # toolchain "leanprover/lean4:v4.33.1" -> "leanprover--lean4---v4.33.1"
        expected = self._cfg.lean.toolchain.replace("/", "--").replace(":", "---")
        for d in dirs:
            if d.name == expected:
                return d
        return None

    def create_session(self) -> None:
        """Spawn the persistent Lean process and wait for readiness (s14)."""
        if self._proc is not None and self._proc.poll() is None:
            return
        args = [str(self._exe), "--imports", ",".join(self._imports)]
        cmd = [str(self._elan_home / "bin" / "lake.exe"), "env", *args]
        self._proc = subprocess.Popen(
            cmd,
            cwd=self._package_dir,
            env=self._process_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
        self._queue = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        ready = self._recv(self._cfg.interactive.startup_timeout_seconds)
        if ready is None:
            self.close()
            raise BackendCrash(
                "REPL did not become ready (startup timeout)",
                FailureClass.INFRASTRUCTURE_FAILURE,
            )
        if ready.get("error"):
            self.close()
            raise BackendCrash(f"REPL startup failed: {ready['error']}", FailureClass.LEAN_FAILURE)
        self._state = ProofState(status="ready")

    def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            self._queue.put(line.strip())
        self._queue.put(None)  # EOF sentinel

    def _recv(self, timeout: float) -> dict | None:
        try:
            line = self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
        if line is None:
            return None
        return json.loads(line)

    def _send(self, payload: dict, timeout: float) -> dict:
        if self._proc is None or self._proc.poll() is not None:
            raise BackendCrash("REPL process is not running", FailureClass.INFRASTRUCTURE_FAILURE)
        assert self._proc.stdin is not None
        try:
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise BackendCrash(f"REPL stdin write failed: {e}", FailureClass.INFRASTRUCTURE_FAILURE) from e
        resp = self._recv(timeout)
        if resp is None:
            self.close()
            code = self._proc.poll() if self._proc else None
            raise BackendCrash(
                f"REPL died or timed out (exit code: {code})", FailureClass.LEAN_FAILURE
            )
        return resp

    # ------------------------------------------------------------------ #
    # spec section 14 interface
    # ------------------------------------------------------------------ #

    def load_environment(self, imports: tuple[str, ...]) -> None:
        """Environment is fixed per session (section 11); changing it
        requires a new session (reset)."""
        if tuple(imports) != self._imports:
            self._imports = tuple(imports)
            self.reset()

    def submit_action(self, action: str, *, update_env: bool = True) -> ActionResult:
        """Submit a Lean source fragment; returns the s14 action record.

        Import statements are stripped: the session environment is fixed at
        spawn (section 11); imports belong to session creation, not actions.
        """
        action = _strip_imports(action)
        previous_state = self._state
        started = time.perf_counter()
        try:
            resp = self._send(
                {"op": "verify", "source": action, "update_env": update_env},
                timeout=self._cfg.interactive.action_timeout_seconds,
            )
        except BackendCrash as e:
            next_state = ProofState(status="crashed")
            return ActionResult(
                previous_state=previous_state,
                action=action,
                next_state=next_state,
                errors=[Diagnostic(severity="error", line=None, column=None, message=str(e))],
                execution_time=time.perf_counter() - started,
                status=ProofStatus.RESOURCE_LIMIT,
                failure_class=e.failure_class,
                source_hash=source_hash(action),
            )
        execution_time = time.perf_counter() - started

        if resp.get("error"):
            diag = Diagnostic(severity="error", line=None, column=None, message=resp["error"])
            self._state = ProofState(status="infrastructure_error", errors=[diag])
            return ActionResult(
                previous_state=previous_state,
                action=action,
                next_state=self._state,
                errors=[diag],
                execution_time=execution_time,
                status=ProofStatus.RESOURCE_LIMIT,
                failure_class=FailureClass.LEAN_FAILURE,
                source_hash=source_hash(action),
            )

        messages = resp.get("messages", []) or []
        errors = [_parse_serialized_message(m) for m in messages if m.get("severity") == "error"]
        infos = [str(m.get("data", "")) for m in messages if m.get("severity") == "information"]
        ok = resp.get("status") == "success"
        self._state = ProofState(
            status="success" if ok else "error",
            errors=errors,
            infos=infos,
        )
        return ActionResult(
            previous_state=previous_state,
            action=action,
            next_state=self._state,
            errors=errors,
            execution_time=execution_time,
            status=ProofStatus.SUCCESS if ok else ProofStatus.FAIL_TYPECHECK,
            failure_class=None if ok else FailureClass.MODEL_FAILURE,
            source_hash=source_hash(action),
        )

    def get_proof_state(self) -> ProofState:
        return self._state

    def get_errors(self) -> list[Diagnostic]:
        return list(self._state.errors)

    def reset(self) -> None:
        """Fresh session: kill and respawn the process (imports fixed at spawn)."""
        self.close()
        self.create_session()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._send({"op": "close"}, timeout=5)
                except BackendCrash:
                    pass
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
        finally:
            self._closed = False
            self._proc = None


class InteractiveBackend:
    """Session factory/manager (section 14)."""

    def __init__(self, config: Config, environment: LeanEnvironment):
        self._cfg = config
        self._env = environment

    def open_session(self, imports: tuple[str, ...] = ("Mathesis.Basic",)) -> InteractiveSession:
        return InteractiveSession(self._cfg, self._env, imports=imports)
