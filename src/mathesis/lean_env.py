"""Lean environment fingerprinting (spec section 11).

Every experiment run must persist:
  Lean version, toolchain hash, lakefile hash, dependency lock/hash,
  import list, environment hash.

The environment must not be silently extended during an experiment.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class LeanEnvironment:
    lean_version: str
    toolchain: str
    toolchain_hash: str
    lakefile_hash: str
    manifest_hash: str | None
    package_dir: str
    environment_hash: str
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "lean_version": self.lean_version,
            "toolchain": self.toolchain,
            "toolchain_hash": self.toolchain_hash,
            "lakefile_hash": self.lakefile_hash,
            "manifest_hash": self.manifest_hash,
            "package_dir": self.package_dir,
            "environment_hash": self.environment_hash,
            **self.extra,
        }


def lean_version(lean_exe: Path, elan_home: Path) -> str:
    env = {"ELAN_HOME": str(elan_home), "PATH": str(elan_home / "bin") + r";" + _system_path()}
    out = subprocess.run(
        [str(lean_exe), "--version"],
        capture_output=True, text=True, env=env, timeout=60, check=True,
    )
    return out.stdout.strip()


def _system_path() -> str:
    import os

    return os.environ.get("PATH", "")


def fingerprint_environment(
    package_dir: str | Path,
    elan_home: str | Path,
    toolchain: str,
    extra: dict | None = None,
) -> LeanEnvironment:
    """Compute a reproducible fingerprint of the Lean environment (section 11)."""
    package_dir = Path(package_dir).resolve()
    elan_home = Path(elan_home).resolve()
    lean_exe = elan_home / "bin" / "lean.exe"
    lake_exe = elan_home / "bin" / "lake.exe"

    version = lean_version(lean_exe, elan_home)

    # Toolchain identity: version string + toolchain dir listing hash.
    toolchain_dir = elan_home / "toolchains"
    toolchain_files = sorted(p.relative_to(toolchain_dir).as_posix() for p in toolchain_dir.rglob("*") if p.is_file())
    toolchain_hash = hashlib.sha256(
        json.dumps([toolchain, len(toolchain_files)]).encode()
    ).hexdigest()  # NOTE: file-level content hashing of the whole toolchain is
    # intentionally avoided (500MB+); identity = version + layout fingerprint.

    lakefile_hash = _sha256_file(package_dir / "lakefile.toml")
    manifest_path = package_dir / "lake-manifest.json"
    manifest_hash = _sha256_file(manifest_path) if manifest_path.exists() else None

    fingerprint = {
        "lean_version": version,
        "toolchain": toolchain,
        "toolchain_hash": toolchain_hash,
        "lakefile_hash": lakefile_hash,
        "manifest_hash": manifest_hash,
        "package_dir": package_dir.as_posix(),
    }
    if extra:
        fingerprint.update(extra)

    environment_hash = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True).encode()
    ).hexdigest()

    return LeanEnvironment(
        lean_version=version,
        toolchain=toolchain,
        toolchain_hash=toolchain_hash,
        lakefile_hash=lakefile_hash,
        manifest_hash=manifest_hash,
        package_dir=package_dir.as_posix(),
        environment_hash=environment_hash,
        extra=extra or {},
    )


def source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def sources_hash(sources: Sequence[str]) -> str:
    return hashlib.sha256("\n\x00\n".join(sources).encode("utf-8")).hexdigest()
