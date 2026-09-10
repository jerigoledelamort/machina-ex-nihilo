"""Corpus sample with full provenance (spec sections 23, 19)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from ..provenance import GeneratorProvenance


@dataclass
class CorpusSample:
    sample_id: str
    source: str
    level: str                    # S0 | S1 | S2
    split: Optional[str] = None   # TRAIN | VALIDATION | TEST (s25)
    prop_structure: Optional[str] = None
    proof_structure: Optional[str] = None
    mutation_type: Optional[str] = None
    parent_id: Optional[str] = None
    generator: Optional[GeneratorProvenance] = None
    validation: Optional[dict] = None   # ValidationProvenance.to_dict()
    structure_fingerprint: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sample_id": self.sample_id,
            "source": self.source,
            "level": self.level,
            "split": self.split,
            "prop_structure": self.prop_structure,
            "proof_structure": self.proof_structure,
            "mutation_type": self.mutation_type,
            "parent_id": self.parent_id,
            "generator_provenance": self.generator.to_dict() if self.generator else None,
            "validation_provenance": self.validation,
            "structure_fingerprint": self.structure_fingerprint,
        }


def sample_id_for(level: str, index: int, seed: int, mutated: bool) -> str:
    kind = "m" if mutated else "t"
    return f"{level.lower()}_{kind}{index}_seed{seed}"


def source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
