"""Versioned configuration loading (spec section 62).

All experiment-dependent parameters must live in configuration files.
Hidden magic numbers are forbidden.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path("configs/default.yaml")


@dataclass(frozen=True)
class LeanConfig:
    toolchain: str
    elan_home: str
    package_dir: str


@dataclass(frozen=True)
class BatchConfig:
    timeout_seconds: int
    max_output_bytes: int


@dataclass(frozen=True)
class InteractiveConfig:
    startup_timeout_seconds: int
    action_timeout_seconds: int


@dataclass(frozen=True)
class SafetyConfig:
    forbidden_tokens: tuple[str, ...]
    forbidden_declarations: tuple[str, ...]
    allowed_import_prefixes: tuple[str, ...]
    restricted_patterns: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    lean: LeanConfig
    batch: BatchConfig
    interactive: InteractiveConfig
    trusted_kernel_principles: tuple[str, ...]
    safety: SafetyConfig
    source_path: Path
    source_hash: str
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": str(self.source_path),
            "config_hash": self.source_hash,
            "lean": {
                "toolchain": self.lean.toolchain,
                "elan_home": self.lean.elan_home,
                "package_dir": self.lean.package_dir,
            },
            "validation": {
                "batch": {
                    "timeout_seconds": self.batch.timeout_seconds,
                    "max_output_bytes": self.batch.max_output_bytes,
                },
                "interactive": {
                    "startup_timeout_seconds": self.interactive.startup_timeout_seconds,
                    "action_timeout_seconds": self.interactive.action_timeout_seconds,
                },
            },
            "trusted_kernel_principles": list(self.trusted_kernel_principles),
            "safety": {
                "forbidden_tokens": list(self.safety.forbidden_tokens),
                "forbidden_declarations": list(self.safety.forbidden_declarations),
                "allowed_import_prefixes": list(self.safety.allowed_import_prefixes),
                "restricted_patterns": list(self.safety.restricted_patterns),
            },
        }


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration. Missing values are an error, not silently defaulted."""
    cfg_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config file: {cfg_path}")

    lean = data["lean"]
    validation = data["validation"]
    safety = data["safety"]

    return Config(
        lean=LeanConfig(
            toolchain=str(lean["toolchain"]),
            elan_home=str(lean["elan_home"]),
            package_dir=str(lean["package_dir"]),
        ),
        batch=BatchConfig(
            timeout_seconds=int(validation["batch"]["timeout_seconds"]),
            max_output_bytes=int(validation["batch"]["max_output_bytes"]),
        ),
        interactive=InteractiveConfig(
            startup_timeout_seconds=int(validation["interactive"]["startup_timeout_seconds"]),
            action_timeout_seconds=int(validation["interactive"]["action_timeout_seconds"]),
        ),
        trusted_kernel_principles=tuple(validation["trusted_kernel_principles"]),
        safety=SafetyConfig(
            forbidden_tokens=tuple(safety["forbidden_tokens"]),
            forbidden_declarations=tuple(safety["forbidden_declarations"]),
            allowed_import_prefixes=tuple(safety["allowed_import_prefixes"]),
            restricted_patterns=tuple(safety["restricted_patterns"]),
        ),
        source_path=cfg_path,
        source_hash=_hash_bytes(cfg_path.read_bytes()),
        raw=data,
    )


def config_fingerprint(cfg: Config) -> str:
    """Stable hash of the effective configuration (for experiment metadata)."""
    return _hash_bytes(json.dumps(cfg.to_dict(), sort_keys=True).encode("utf-8"))
