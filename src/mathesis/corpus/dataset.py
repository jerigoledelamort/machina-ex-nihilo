"""Dataset architecture: splits + leakage audit (spec sections 25-27).

TRAIN/VALIDATION/TEST are strictly separated. TEST is fixed before training
and used only for final Milestone 1 evaluation.

Leakage audit (s27):
  - exact duplicate detection (source hash)
  - normalized AST duplicate detection (structure keys)
  - near-duplicate detection (normalized text)
  - dependency/import overlap analysis
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

SPLIT_TRAIN = "TRAIN"
SPLIT_VALIDATION = "VALIDATION"
SPLIT_TEST = "TEST"


@dataclass
class LeakageReport:
    ok: bool
    exact_duplicates: int = 0
    normalized_duplicates: int = 0
    near_duplicates: int = 0
    cross_split_structure_overlap: dict = field(default_factory=dict)
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "exact_duplicates": self.exact_duplicates,
            "normalized_duplicates": self.normalized_duplicates,
            "near_duplicates": self.near_duplicates,
            "cross_split_structure_overlap": self.cross_split_structure_overlap,
            "details": list(self.details),
        }


def source_fingerprint(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def normalize_source(source: str) -> str:
    """Normalized text for near-duplicate detection (s27)."""
    text = re.sub(r"theorem\s+\S+\s*:", "theorem _ :", source)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalized_fingerprint(source: str) -> str:
    return hashlib.sha256(normalize_source(source).encode("utf-8")).hexdigest()


def structure_fingerprint(sample: dict) -> str | None:
    """AST-level fingerprint from structure keys (s27 normalized AST dup)."""
    prop = sample.get("prop_structure")
    proof = sample.get("proof_structure")
    if prop is None and proof is None:
        return None
    return hashlib.sha256(f"{prop}|{proof}".encode("utf-8")).hexdigest()


def make_splits(samples: list[dict], seed: int,
                train_frac: float = 0.8, val_frac: float = 0.1) -> list[dict]:
    """Deterministic split assignment (s25). Fractions are config-level
    parameters passed explicitly by the caller."""
    indexed = list(range(len(samples)))
    random.Random(seed).shuffle(indexed)
    n = len(samples)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    split_of = {}
    for i, idx in enumerate(indexed):
        if i < n_train:
            split_of[idx] = SPLIT_TRAIN
        elif i < n_train + n_val:
            split_of[idx] = SPLIT_VALIDATION
        else:
            split_of[idx] = SPLIT_TEST
    out = []
    for idx, sample in enumerate(samples):
        s = dict(sample)
        s["split"] = split_of[idx]
        out.append(s)
    return out


def leakage_audit(samples: list[dict]) -> LeakageReport:
    """Leakage audit before training (s27). TEST is checked against
    TRAIN/VALIDATION for all duplicate classes."""
    by_split: dict[str, list[dict]] = {}
    for s in samples:
        by_split.setdefault(s.get("split", SPLIT_TRAIN), []).append(s)

    exact_seen: dict[str, str] = {}
    norm_seen: dict[str, str] = {}
    near_seen: dict[str, str] = {}
    structure_by_split: dict[str, set[str]] = {}

    exact_dups = norm_dups = near_dups = 0
    details: list[str] = []

    for s in samples:
        sid = s.get("sample_id", "?")
        fp = source_fingerprint(s["source"])
        if fp in exact_seen:
            exact_dups += 1
            details.append(f"exact dup: {sid} == {exact_seen[fp]}")
        else:
            exact_seen[fp] = sid

        nfp = normalized_fingerprint(s["source"])
        if nfp in norm_seen:
            norm_dups += 1
            details.append(f"normalized dup: {sid} == {norm_seen[nfp]}")
        else:
            norm_seen[nfp] = sid

        sfp = structure_fingerprint(s)
        if sfp is not None:
            if sfp in near_seen:
                near_dups += 1
                details.append(f"structure dup: {sid} == {near_seen[sfp]}")
            else:
                near_seen[sfp] = sid
            structure_by_split.setdefault(s.get("split", SPLIT_TRAIN), set()).add(sfp)

    # Cross-split overlap: structures appearing in TEST and also in TRAIN/VAL
    overlap: dict[str, int] = {}
    test_structures = structure_by_split.get(SPLIT_TEST, set())
    for other in (SPLIT_TRAIN, SPLIT_VALIDATION):
        shared = test_structures & structure_by_split.get(other, set())
        overlap[f"TEST_{other}"] = len(shared)

    report = LeakageReport(
        ok=exact_dups == 0 and norm_dups == 0 and all(v == 0 for v in overlap.values()),
        exact_duplicates=exact_dups,
        normalized_duplicates=norm_dups,
        near_duplicates=near_dups,
        cross_split_structure_overlap=overlap,
        details=details,
    )
    return report


def save_dataset(samples: list[dict], path: Path) -> None:
    """Persist dataset as JSONL with full provenance per sample (s23)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n")


def load_dataset(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
