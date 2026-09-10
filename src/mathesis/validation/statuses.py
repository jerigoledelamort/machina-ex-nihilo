"""Proof validation statuses (spec sections 12, 64).

Infrastructure errors must never be interpreted as mathematical FAIL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProofStatus(str, Enum):
    """Status of a candidate proof verification (section 12)."""

    SUCCESS = "SUCCESS"
    FAIL_PARSE = "FAIL_PARSE"
    FAIL_SAFETY = "FAIL_SAFETY"
    FAIL_TYPECHECK = "FAIL_TYPECHECK"
    FAIL_KERNEL = "FAIL_KERNEL"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"


class FailureClass(str, Enum):
    """Failure attribution classes (section 64).

    A Lean process crash is NOT a mathematical refutation.
    """

    MODEL_FAILURE = "MODEL_FAILURE"
    LEAN_FAILURE = "LEAN_FAILURE"
    INFRASTRUCTURE_FAILURE = "INFRASTRUCTURE_FAILURE"
    TIMEOUT = "TIMEOUT"
    RESOURCE_FAILURE = "RESOURCE_FAILURE"
    INVALID_ACTION = "INVALID_ACTION"


# Which failure class each non-SUCCESS status maps to by default.
STATUS_TO_FAILURE_CLASS: dict[ProofStatus, FailureClass] = {
    ProofStatus.FAIL_PARSE: FailureClass.MODEL_FAILURE,
    ProofStatus.FAIL_SAFETY: FailureClass.INVALID_ACTION,
    ProofStatus.FAIL_TYPECHECK: FailureClass.MODEL_FAILURE,
    ProofStatus.FAIL_KERNEL: FailureClass.MODEL_FAILURE,
    ProofStatus.TIMEOUT: FailureClass.TIMEOUT,
    ProofStatus.RESOURCE_LIMIT: FailureClass.RESOURCE_FAILURE,
}


@dataclass
class Diagnostic:
    """Normalized single Lean diagnostic."""

    severity: str  # "error" | "warning" | "info"
    line: int | None
    column: int | None
    message: str
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "line": self.line,
            "column": self.column,
            "message": self.message,
        }


@dataclass
class VerificationResult:
    """Full result of one verification attempt, with provenance fields."""

    status: ProofStatus
    failure_class: FailureClass | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    # Kernel principles the proof depends on, e.g. Classical.choice (section 9)
    kernel_axioms: list[str] = field(default_factory=list)
    # Restricted mechanisms actually used (e.g. native_decide), empty if none
    restricted_mechanisms: list[str] = field(default_factory=list)
    wall_time_seconds: float = 0.0
    source_hash: str = ""
    environment_hash: str = ""
    exit_code: int | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status is ProofStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "kernel_axioms": list(self.kernel_axioms),
            "restricted_mechanisms": list(self.restricted_mechanisms),
            "wall_time_seconds": round(self.wall_time_seconds, 6),
            "source_hash": self.source_hash,
            "environment_hash": self.environment_hash,
            "exit_code": self.exit_code,
            "notes": list(self.notes),
        }
