"""Tokenizer A/B benchmark (spec sections 28-30).

A: BPE (trained on Mathesis corpus)
B: Lean-aware tokenizer

Metrics (s30): vocabulary size, average tokens/declaration, tokens/proof,
tokens/error, compression ratio, training throughput, inference throughput.

Decision criterion (s30, pre-registered): Lean-aware tokenizer is chosen only
if it shows >= 20% better compression ratio on the representative corpus;
otherwise BPE becomes the default. Result goes to DECISIONS.md.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from mathesis.tokenizers import BPETokenizer, LeanTokenizer  # noqa: E402


def compression_ratio(texts: list[str], token_lists: list[list[str]]) -> float:
    total_chars = sum(len(t) for t in texts)
    total_tokens = sum(len(toks) for toks in token_lists)
    return total_chars / total_tokens if total_tokens else 0.0


def throughput(texts: list[str], encode_fn) -> float:
    t0 = time.perf_counter()
    n = 0
    for t in texts:
        encode_fn(t)
        n += len(t)
    return n / (time.perf_counter() - t0)  # chars/sec


def main() -> int:
    parser = argparse.ArgumentParser(description="Tokenizer A/B benchmark (s28-s30)")
    parser.add_argument("--corpus", default="data/corpus_tokenizer.jsonl")
    parser.add_argument("--bpe-vocab", type=int, default=8000)
    parser.add_argument("--output-dir", default="benchmarks/results")
    args = parser.parse_args()

    corpus_path = WORKSPACE / args.corpus
    samples = [json.loads(l) for l in corpus_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    declarations = [s["source"] for s in samples]
    proofs = [s["source"].split(":=", 1)[-1].strip() for s in samples if ":=" in s["source"]]
    errors = [
        e.get("message", "") or e.get("raw_message", "")
        for s in samples
        for e in [((s.get("validation_provenance") or {}).get("errors") or [None])[0]]
        if e
    ]
    errors = [e for e in errors if e]

    # ---------------- BPE (Option A) ----------------
    t0 = time.perf_counter()
    bpe = BPETokenizer(vocab_size=args.bpe_vocab)
    # train on TRAIN split only (no test leakage into tokenizer training)
    train_files = [corpus_path]
    bpe.train_from_files(train_files)
    bpe_train_s = time.perf_counter() - t0

    bpe_decls = [bpe.tokenize(t) for t in declarations]
    bpe_proofs = [bpe.tokenize(t) for t in proofs]
    bpe_errors = [bpe.tokenize(t) for t in errors]

    # ---------------- Lean-aware (Option B) ----------------
    t0 = time.perf_counter()
    lean = LeanTokenizer()
    lean_setup_s = time.perf_counter() - t0
    lean_decls = [lean.tokenize(t) for t in declarations]
    lean_proofs = [lean.tokenize(t) for t in proofs]
    lean_errors = [lean.tokenize(t) for t in errors]

    def avg(tokens: list[list[str]]) -> float:
        return round(statistics.mean(len(t) for t in tokens), 3) if tokens else 0.0

    report = {
        "spec": "MATHESIS Milestone 1, sections 28-30",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "corpus": str(corpus_path),
        "n_declarations": len(declarations),
        "n_proofs": len(proofs),
        "n_errors": len(errors),
        "bpe": {
            "vocab_size": bpe.vocab_size,
            "train_seconds": round(bpe_train_s, 3),
            "tokens_per_declaration": avg(bpe_decls),
            "tokens_per_proof": avg(bpe_proofs),
            "tokens_per_error": avg(bpe_errors),
            "compression_ratio": round(compression_ratio(declarations, bpe_decls), 3),
            "inference_chars_per_sec": round(
                throughput(declarations[:200], bpe.encode), 1
            ),
        },
        "lean_aware": {
            "vocab_size": lean.vocab_size,
            "setup_seconds": round(lean_setup_s, 6),
            "tokens_per_declaration": avg(lean_decls),
            "tokens_per_proof": avg(lean_proofs),
            "tokens_per_error": avg(lean_errors),
            "compression_ratio": round(compression_ratio(declarations, lean_decls), 3),
            "inference_chars_per_sec": round(
                throughput(declarations[:200], lean.encode), 1
            ),
        },
    }

    cr_bpe = report["bpe"]["compression_ratio"]
    cr_lean = report["lean_aware"]["compression_ratio"]
    improvement = (cr_lean - cr_bpe) / cr_bpe if cr_bpe else 0.0
    report["compression_improvement_pct"] = round(improvement * 100, 2)
    # pre-registered criterion (s30)
    report["decision"] = "lean_aware" if improvement >= 0.20 else "bpe"
    report["criterion"] = "lean_aware requires >= 20% compression ratio improvement"

    out_dir = WORKSPACE / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"tokenizer_benchmark_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # persist the chosen tokenizer artifacts
    bpe.save(out_dir / "bpe_tokenizer.json")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
