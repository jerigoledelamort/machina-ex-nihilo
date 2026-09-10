"""Lean benchmark (spec sections 16-17).

Compares batch / interactive / warm interactive on Tiny/Medium/Large.
Measures: process startup, full verification time, per-action time,
checks/sec, mean/p50/p95/p99, clean rebuild cost.
Results are saved as a machine-readable JSON report.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from mathesis.bench.generator import generate_action_sequence, generate_source  # noqa: E402
from mathesis.config import load_config  # noqa: E402
from mathesis.lean_env import fingerprint_environment  # noqa: E402
from mathesis.validation import BatchBackend, InteractiveSession  # noqa: E402


def stats(times: list[float]) -> dict:
    if not times:
        return {}
    ordered = sorted(times)
    n = len(ordered)

    def pct(p: float) -> float:
        k = max(0, min(n - 1, int(round(p * (n - 1)))))
        return ordered[k]

    return {
        "n": n,
        "mean_s": round(statistics.mean(ordered), 6),
        "p50_s": round(pct(0.50), 6),
        "p95_s": round(pct(0.95), 6),
        "p99_s": round(pct(0.99), 6),
        "min_s": round(ordered[0], 6),
        "max_s": round(ordered[-1], 6),
        "checks_per_sec": round(n / sum(ordered), 3) if sum(ordered) > 0 else None,
    }


def bench_batch(config, environment, files: dict[str, Path], repeats: int) -> dict:
    backend = BatchBackend(config, environment)
    out = {}
    for name, path in files.items():
        # warmup discard
        backend.verify_file(path)
        times = []
        ok = 0
        for _ in range(repeats):
            r = backend.verify_file(path)
            times.append(r.wall_time_seconds)
            ok += int(r.success)
        entry = stats(times)
        entry["success_rate"] = ok / repeats
        entry["size_bytes"] = path.stat().st_size
        out[name] = entry
    return out


def bench_interactive_cold(config, environment, files: dict[str, Path]) -> dict:
    """Cold interactive: session startup + one verification per file."""
    out = {}
    for name, path in files.items():
        t0 = time.perf_counter()
        session = InteractiveSession(config, environment)
        startup = time.perf_counter() - t0
        source = path.read_text(encoding="utf-8")
        result = session.submit_action(source, update_env=False)
        out[name] = {
            "startup_s": round(startup, 6),
            "verify_s": round(result.execution_time, 6),
            "total_s": round(startup + result.execution_time, 6),
            "status": result.status.value,
        }
        session.close()
    return out


def bench_interactive_warm(config, environment, files: dict[str, Path], runs: int) -> dict:
    """Warm interactive: persistent session, repeated verification."""
    session = InteractiveSession(config, environment)
    out = {}
    try:
        for name, path in files.items():
            source = path.read_text(encoding="utf-8")
            session.submit_action("theorem warmup_probe : MTrue := MTrue.intro", update_env=False)
            times = []
            for _ in range(runs):
                r = session.submit_action(source, update_env=False)
                times.append(r.execution_time)
            entry = stats(times)
            entry["size_bytes"] = path.stat().st_size
            out[name] = entry
    finally:
        session.close()
    return out


def bench_throughput(config, environment, n_actions: int) -> dict:
    """Search throughput (s17): realistic sequential actions per second."""
    session = InteractiveSession(config, environment)
    try:
        actions = generate_action_sequence(n_actions)
        times = []
        statuses = {}
        for action in actions:
            r = session.submit_action(action, update_env=True)
            times.append(r.execution_time)
            statuses[r.status.value] = statuses.get(r.status.value, 0) + 1
        total = sum(times)
        return {
            "n_actions": len(actions),
            "total_s": round(total, 6),
            "actions_per_sec": round(len(actions) / total, 3),
            "per_action": stats(times),
            "status_histogram": statuses,
        }
    finally:
        session.close()


def bench_clean_rebuild(config) -> dict:
    lake = Path(config.lean.elan_home).resolve() / "bin" / "lake.exe"
    pkg = Path(config.lean.package_dir).resolve()
    env = os.environ.copy()
    env["ELAN_HOME"] = str(Path(config.lean.elan_home).resolve())
    t0 = time.perf_counter()
    subprocess.run([str(lake), "clean"], cwd=pkg, env=env, check=True,
                   capture_output=True, timeout=600)
    clean_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    subprocess.run([str(lake), "build"], cwd=pkg, env=env, check=True,
                   capture_output=True, timeout=1800)
    build_s = time.perf_counter() - t0
    return {"clean_s": round(clean_s, 6), "build_s": round(build_s, 6),
            "total_s": round(clean_s + build_s, 6)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Lean benchmark (s16-s17)")
    parser.add_argument("--config", default=None)
    parser.add_argument("--output-dir", default="benchmarks/results")
    args = parser.parse_args()

    config = load_config(args.config)
    environment = fingerprint_environment(
        WORKSPACE / config.lean.package_dir,
        WORKSPACE / config.lean.elan_home,
        config.lean.toolchain,
    )

    bench_dir = WORKSPACE / ".runs" / "bench"
    bench_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for size_name, n in config.benchmark.sizes.items():
        p = bench_dir / f"bench_{size_name}.lean"
        p.write_text(generate_source(n), encoding="utf-8")
        files[size_name] = p

    report: dict = {
        "spec": "MATHESIS Milestone 1, sections 16-17",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": environment.to_dict(),
        "config_hash": config.source_hash,
    }

    print("[1/5] batch...", flush=True)
    report["batch"] = bench_batch(config, environment, files, config.benchmark.batch_repeats)
    print("[2/5] interactive cold...", flush=True)
    report["interactive_cold"] = bench_interactive_cold(config, environment, files)
    print("[3/5] interactive warm...", flush=True)
    report["interactive_warm"] = bench_interactive_warm(
        config, environment, files, config.benchmark.warm_runs
    )
    print("[4/5] search throughput...", flush=True)
    report["search_throughput"] = bench_throughput(
        config, environment, config.benchmark.throughput_actions
    )
    if config.benchmark.measure_clean_rebuild:
        print("[5/5] clean rebuild...", flush=True)
        report["clean_rebuild"] = bench_clean_rebuild(config)

    out_dir = WORKSPACE / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"lean_benchmark_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSaved: {out_path}\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
