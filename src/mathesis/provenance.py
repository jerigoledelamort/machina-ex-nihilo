"""Provenance model (spec section 23).

Never use a single `provenance` field. Each sample carries at minimum:
  - generator_provenance (how the candidate was produced)
  - validation_provenance (how it was checked)

Examples:
  generator_provenance = synthetic            validation_provenance = verified_by_lean
  generator_provenance = synthetic_mutation   validation_provenance = rejected_by_lean
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GeneratorProvenance:
    origin: str                      # e.g. "synthetic", "synthetic_mutation"
    generator_version: str
    seed: int | None = None
    level: str | None = None         # S0 | S1 | S2 (section 20)
    parent_id: str | None = None
    mutation_type: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationProvenance:
    verdict: str                     # e.g. "verified_by_lean", "rejected_by_lean"
    status: str                      # ProofStatus value
    environment_hash: str
    source_hash: str
    lean_version: str
    kernel_axioms: list[str] = field(default_factory=list)
    restricted_mechanisms: list[str] = field(default_factory=list)
    wall_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SampleProvenance:
    sample_id: str
    generator: GeneratorProvenance
    validation: ValidationProvenance | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "generator_provenance": self.generator.to_dict(),
            "validation_provenance": self.validation.to_dict() if self.validation else None,
        }
