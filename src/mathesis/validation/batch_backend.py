"""Batch Lean backend (spec section 15).

Interface: verify_file(path, environment) -> VerificationResult

Batch verification must be reproducible: fresh process, fixed environment,
fixed dependencies. Interactive SUCCESS never replaces batch verification
(section 13).
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from ..config import Config
from ..lean_env import LeanEnvironment, source_hash
from . import safety
from .statuses import STATUS_TO_FAILURE_CLASS, Diagnostic, ProofStatus, VerificationResult


class BatchBackend:
    def __init__(self, config: Config, environment: LeanEnvironment):
        self._cfg = config
        self._env = environment
        self._package_dir = Path(config.lean.package_dir).resolve()
        self._lake_exe = Path(config.lean.elan_home).resolve() / "bin" / "lake.exe"

    def _process_env(self) -> dict:
        env = os.environ.copy()
        env["ELAN_HOME"] = str(Path(self._cfg.lean.elan_home).resolve())
        return env

    def verify_file(self, path: str | Path, environment: LeanEnvironment | None = None) -> VerificationResult:
        """Verify a full .lean artifact in a fresh Lean process (section 15)."""
        environment = environment or self._env
        path = Path(path).resolve()
        source = path.read_text(encoding="utf-8")

        result = VerificationResult(
            status=ProofStatus.FAIL_SAFETY,
            source_hash=source_hash(source),
            environment_hash=environment.environment_hash,
        )

        # Stage: safety validation (section 12)
        report = safety.scan_safety(
            source,
            forbidden_tokens=self._cfg.safety.forbidden_tokens,
            forbidden_declarations=self._cfg.safety.forbidden_declarations,
            restricted_patterns=self._cfg.safety.restricted_patterns,
        )
        if not report.ok:
            result.diagnostics.append(
                Diagnostic(severity="error", line=None, column=None,
                           message="; ".join(report.violations))
            )
            result.restricted_mechanisms = list(report.restricted_uses)
            result.failure_class = STATUS_TO_FAILURE_CLASS[result.status]
            return result

        # Stage: import validation (section 12)
        import_violations = safety.validate_imports(
            source, allowed_prefixes=self._cfg.safety.allowed_import_prefixes
        )
        if import_violations:
            result.diagnostics.append(
                Diagnostic(severity="error", line=None, column=None,
                           message="; ".join(import_violations))
            )
            result.failure_class = STATUS_TO_FAILURE_CLASS[result.status]
            return result

        # Stages: elaboration + kernel verification in a fresh process.
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [str(self._lake_exe), "env", "lean", str(path)],
                cwd=self._package_dir,
                env=self._process_env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._cfg.batch.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            result.status = ProofStatus.TIMEOUT
            result.failure_class = STATUS_TO_FAILURE_CLASS[ProofStatus.TIMEOUT]
            result.wall_time_seconds = time.perf_counter() - started
            result.notes.append(f"timeout after {self._cfg.batch.timeout_seconds}s")
            return result
        result.wall_time_seconds = time.perf_counter() - started
        result.exit_code = proc.returncode

        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        result.diagnostics = parse_diagnostics(output)

        if proc.returncode == 0:
            result.status = ProofStatus.SUCCESS
            result.kernel_axioms = sorted(
                {
                    ax
                    for deps in safety.parse_print_axioms(output).values()
                    for ax in deps
                }
            )
        else:
            result.status = classify_failure(result.diagnostics)
            result.failure_class = STATUS_TO_FAILURE_CLASS[result.status]
        return result


_DIAG_RE = None


def parse_diagnostics(output: str) -> list[Diagnostic]:
    """Parse Lean compiler output into normalized diagnostics (section 29).

    Lean 4 format: `<path>:<line>:<col>: <severity>: <message ...>`
    Messages may span multiple lines; continuation lines are appended.
    """
    diagnostics: list[Diagnostic] = []
    current: Diagnostic | None = None
    for raw_line in output.splitlines():
        header = _try_parse_header(raw_line)
        if header is not None:
            if current is not None:
                diagnostics.append(current)
            severity, line, col, msg = header
            current = Diagnostic(severity=severity, line=line, column=col, message=msg, raw=raw_line)
        elif current is not None and raw_line.strip():
            current.message += "\n" + raw_line
            current.raw += "\n" + raw_line
    if current is not None:
        diagnostics.append(current)
    return diagnostics


_DIAG_HEADER_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<col>\d+): (?P<sev>error|warning|info): ?(?P<msg>.*)$"
)


def _try_parse_header(line: str):
    """Parse `<path>:<line>:<col>: <severity>: <msg>` (Windows-drive safe)."""
    match = _DIAG_HEADER_RE.match(line)
    if match is None:
        return None
    return (
        match.group("sev"),
        int(match.group("line")),
        int(match.group("col")),
        match.group("msg").strip(),
    )


_PARSE_PATTERNS = (
    "expected", "unexpected token", "invalid occurrence", "maximum recursion depth",
    "unterminated string", "invalid character",
)
_TYPECHECK_PATTERNS = (
    "type mismatch", "unknown identifier", "unknown constant", "unknown variable",
    "application type mismatch", "failed to synthesize", "type class instance",
    "invalid 'theorem'", "invalid 'def'", "invalid 'inductive'", "invalid 'instance'",
    "has type", "but it is expected to have type", "cannot find synthesis order",
)
_KERNEL_PATTERNS = (
    "kernel", "deep recursion was detected", "excessive memory consumption",
    "deterministic timeout", "maximum number of heartbeats",
)


def classify_failure(diagnostics: list[Diagnostic]) -> ProofStatus:
    """Map diagnostics to a ProofStatus (section 12).

    Uncategorizable elaboration errors conservatively map to FAIL_TYPECHECK;
    the raw messages are always preserved in diagnostics.
    """
    errors = [d for d in diagnostics if d.severity == "error"]
    if not errors:
        return ProofStatus.FAIL_TYPECHECK
    text = "\n".join(d.message for d in errors).lower()

    # Order matters: type errors often contain the word "expected"
    # ("but is expected to have type"), so typecheck patterns are checked
    # before parse patterns.
    if any(p in text for p in _KERNEL_PATTERNS):
        return ProofStatus.FAIL_KERNEL
    if any(p in text for p in _TYPECHECK_PATTERNS):
        return ProofStatus.FAIL_TYPECHECK
    if any(p in text for p in _PARSE_PATTERNS):
        return ProofStatus.FAIL_PARSE
    return ProofStatus.FAIL_TYPECHECK
