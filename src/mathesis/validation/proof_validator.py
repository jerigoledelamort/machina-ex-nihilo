"""Proof validation pipeline (spec section 12).

    Candidate
      -> Parsing
      -> Safety validation
      -> Import validation
      -> Elaboration
      -> Kernel verification
      -> Trusted-base inspection
      -> Result

Also exposes the two validation modes (section 13):
  - batch  (final verification, reproduction, milestone artifacts)
  - interactive (proof search, process reward) - implemented in a later stage;
    interactive SUCCESS never replaces batch verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import Config
from ..lean_env import LeanEnvironment, source_hash
from . import safety
from .batch_backend import BatchBackend
from .statuses import Diagnostic, ProofStatus, VerificationResult


@dataclass
class ValidatorPaths:
    scratch_dir: Path


class ProofValidator:
    """Full validation pipeline for candidate proofs (section 12)."""

    def __init__(self, config: Config, environment: LeanEnvironment, scratch_dir: str | Path = ".runs/scratch"):
        self._cfg = config
        self._env = environment
        self._batch = BatchBackend(config, environment)
        self._scratch = Path(scratch_dir)
        self._scratch.mkdir(parents=True, exist_ok=True)

    def verify_source(self, source: str, *, task_id: str = "candidate") -> VerificationResult:
        """Verify an in-memory candidate by materializing it into scratch."""
        path = self._scratch / f"{task_id}.lean"
        path.write_text(source, encoding="utf-8")
        return self.verify_file(path)

    def verify_file(self, path: str | Path) -> VerificationResult:
        result = self._batch.verify_file(path, self._env)
        if result.status is not ProofStatus.SUCCESS:
            return result

        # Stage: trusted-base inspection (section 9).
        # The batch backend already parsed `#print axioms` output; anything
        # outside the trusted kernel principles is a hard violation.
        violations = []
        for dep_decl, axioms in safety.parse_print_axioms(
            "\n".join(d.raw for d in result.diagnostics)
        ).items():
            trusted, viol = safety.inspect_trusted_base({dep_decl: axioms})
            result.kernel_axioms = sorted(set(result.kernel_axioms) | set(trusted))
            violations.extend(viol)
        if violations:
            result.status = ProofStatus.FAIL_SAFETY
            result.diagnostics.append(
                Diagnostic(severity="error", line=None, column=None,
                           message="; ".join(violations))
            )
        return result

    def verify_candidate(self, source: str, *, task_id: str = "candidate") -> VerificationResult:
        """Alias keeping explicit candidate semantics (section 12)."""
        result = self.verify_source(source, task_id=task_id)
        result.source_hash = result.source_hash or source_hash(source)
        return result
