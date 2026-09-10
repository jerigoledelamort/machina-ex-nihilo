"""Corpus generation CLI (spec sections 19-27).

Generates S0/S1/S2 samples + mutation-based plausible errors, validates every
sample with Lean (interactive for bulk, batch for TEST per section 13),
audits the corpus, makes deterministic splits, runs the leakage audit and
persists a JSONL dataset with full provenance.

Usage:
  python scripts/generate_corpus.py --n-per-level 30 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from mathesis.config import load_config  # noqa: E402
from mathesis.corpus import (  # noqa: E402
    GENERATORS,
    GENERATOR_VERSION,
    SPLIT_TEST,
    audit_corpus,
    audit_generator_source,
    leakage_audit,
    make_splits,
    save_dataset,
)
from mathesis.corpus.generator import mutate_sample  # noqa: E402
from mathesis.corpus.sample import sample_id_for  # noqa: E402
from mathesis.lean_env import fingerprint_environment  # noqa: E402
from mathesis.provenance import GeneratorProvenance  # noqa: E402
from mathesis.validation import BatchBackend, InteractiveSession  # noqa: E402
import random  # noqa: E402


def validate_interactive(session: InteractiveSession, source: str) -> dict:
    result = session.submit_action(source, update_env=False)
    return {
        "verdict": "verified_by_lean" if result.status.value == "SUCCESS" else "rejected_by_lean",
        "mode": "interactive",
        "status": result.status.value,
        "environment_hash": session._env_meta.environment_hash,
        "source_hash": result.source_hash,
        "lean_version": session._env_meta.lean_version,
        "errors": [e.to_dict() for e in result.errors],
    }


def validate_batch(backend: BatchBackend, path: Path, environment) -> dict:
    """Batch re-verification. Corpus samples are action-level fragments
    without imports (the interactive session loads the environment at
    spawn); batch files need the explicit import header (s11/s15)."""
    result = backend.verify_file(path, environment)
    return {
        "verdict": "verified_by_lean" if result.success else "rejected_by_lean",
        "mode": "batch",
        "status": result.status.value,
        "environment_hash": environment.environment_hash,
        "source_hash": result.source_hash,
        "lean_version": environment.lean_version,
        "kernel_axioms": result.kernel_axioms,
        "errors": [e.to_dict() for e in result.diagnostics if e.severity == "error"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Mathesis corpus (s19-s27)")
    parser.add_argument("--n-per-level", type=int, default=30)
    parser.add_argument("--n-mutations", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--levels", default="S0,S1,S2")
    parser.add_argument("--output", default="data/corpus_v1.jsonl")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    environment = fingerprint_environment(
        WORKSPACE / config.lean.package_dir,
        WORKSPACE / config.lean.elan_home,
        config.lean.toolchain,
    )
    levels = [lv.strip().upper() for lv in args.levels.split(",")]

    # s22: audit the generator's own source first
    gen_files = [
        WORKSPACE / "src" / "mathesis" / "corpus" / "generator.py",
        WORKSPACE / "src" / "mathesis" / "corpus" / "grammar.py",
    ]
    gen_audit = audit_generator_source(gen_files)
    if not gen_audit.ok:
        print("GENERATOR AUDIT FAILED:", json.dumps(gen_audit.to_dict(), indent=2))
        return 1

    rng = random.Random(args.seed)
    samples = []
    idx = 0
    # s27: do not emit duplicate samples in the first place; dedup key =
    # normalized source fingerprint
    from mathesis.corpus.dataset import normalized_fingerprint

    seen_fingerprints: set[str] = set()

    def _unique(source: str) -> bool:
        fp = normalized_fingerprint(source)
        if fp in seen_fingerprints:
            return False
        seen_fingerprints.add(fp)
        return True

    session = InteractiveSession(config, environment)
    try:
        for level in levels:
            gen = GENERATORS[level]
            emitted = 0
            attempts = 0
            while emitted < args.n_per_level and attempts < args.n_per_level * 20:
                attempts += 1
                s = gen(rng, idx)
                if not _unique(s["source"]):
                    idx += 1
                    continue
                sid = sample_id_for(level, idx, args.seed, mutated=False)
                samples.append({
                    "sample_id": sid,
                    **s,
                    "generator_provenance": GeneratorProvenance(
                        origin="synthetic",
                        generator_version=GENERATOR_VERSION,
                        seed=args.seed,
                        level=level,
                    ).to_dict(),
                })
                idx += 1
                emitted += 1

            # mutations of S2 samples (s24: predominantly mutation-based)
            if level == "S2":
                s2_samples = [s for s in samples if s["level"] == "S2" and "mutation_type" not in s]
                made = 0
                attempts = 0
                while made < args.n_mutations and attempts < args.n_mutations * 20:
                    attempts += 1
                    parent = rng.choice(s2_samples)
                    m = mutate_sample(parent, rng, idx)
                    if m is None or not _unique(m["source"]):
                        idx += 1
                        continue
                    sid = sample_id_for(level, idx, args.seed, mutated=True)
                    samples.append({
                        "sample_id": sid,
                        **m,
                        "generator_provenance": GeneratorProvenance(
                            origin="synthetic_mutation",
                            generator_version=GENERATOR_VERSION,
                            seed=args.seed,
                            level=level,
                            parent_id=parent["sample_id"],
                            mutation_type=m.get("mutation_type"),
                        ).to_dict(),
                    })
                    idx += 1
                    made += 1

        # validate every sample (interactive for bulk speed; s13)
        for s in samples:
            s["validation_provenance"] = validate_interactive(session, s["source"])
    finally:
        session.close()

    # deterministic splits (s25); TEST is fixed here, before any training
    samples = make_splits(samples, seed=args.seed)

    # batch re-verification for TEST samples (s13: interactive does not
    # replace batch verification for final artifacts)
    bench_dir = WORKSPACE / ".runs" / "corpus_check"
    bench_dir.mkdir(parents=True, exist_ok=True)
    backend = BatchBackend(config, environment)
    for s in samples:
        if s.get("split") == SPLIT_TEST:
            p = bench_dir / f"{s['sample_id']}.lean"
            p.write_text("import Mathesis.Basic\n\n" + s["source"], encoding="utf-8")
            s["validation_provenance"] = validate_batch(backend, p, environment)

    # corpus audit (s22)
    corpus_audit = audit_corpus(samples, GENERATOR_VERSION, args.seed)

    # leakage audit (s27)
    leak = leakage_audit(samples)

    # persist
    out_path = WORKSPACE / args.output
    save_dataset(samples, out_path)

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generator_version": GENERATOR_VERSION,
        "seed": args.seed,
        "environment_hash": environment.environment_hash,
        "n_samples": len(samples),
        "generator_audit": gen_audit.to_dict(),
        "corpus_audit": corpus_audit.to_dict(),
        "leakage_audit": leak.to_dict(),
        "output": str(out_path),
        "split_counts": _split_counts(samples),
        "verdict_counts": _verdict_counts(samples),
    }
    summary_path = out_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if gen_audit.ok and corpus_audit.ok else 1


def _split_counts(samples: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for s in samples:
        split = s.get("split", "?")
        counts[split] = counts.get(split, 0) + 1
    return counts


def _verdict_counts(samples: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for s in samples:
        v = (s.get("validation_provenance") or {}).get("verdict", "?")
        counts[v] = counts.get(v, 0) + 1
    return counts


if __name__ == "__main__":
    raise SystemExit(main())
