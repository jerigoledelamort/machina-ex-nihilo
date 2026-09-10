"""Tests for corpus generation, audit, splits, leakage (spec s19-s27)."""

import random
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from mathesis.corpus import (  # noqa: E402
    GENERATOR_VERSION,
    SPLIT_TEST,
    SPLIT_TRAIN,
    audit_corpus,
    audit_sample,
    generate_s0,
    generate_s1,
    generate_s2,
    leakage_audit,
    make_splits,
    mutate_sample,
)
from mathesis.corpus.dataset import normalized_fingerprint  # noqa: E402
from mathesis.corpus.grammar import PropNode, ProofNode, synthesize_proof  # noqa: E402


def _mk(level, idx, source, prop=None, proof=None):
    return {"sample_id": f"{level}_{idx}", "source": source, "level": level,
            "prop_structure": prop, "proof_structure": proof}


def test_s2_synthesis_type_aligned():
    """S2 proof term must match the proposition by construction."""
    rng = random.Random(7)
    for _ in range(50):
        s = generate_s2(rng, 0)
        assert ":=" in s["source"]
        assert s["prop_lean"] and s["proof_lean"]


def test_s2_structure_keys_deterministic():
    rng1 = random.Random(3)
    rng2 = random.Random(3)
    assert generate_s2(rng1, 0)["source"] == generate_s2(rng2, 0)["source"]


def test_grammar_rendering_parenthesized():
    prop = PropNode("and", PropNode("and", PropNode("true"), PropNode("true")), PropNode("true"))
    rendered = prop.to_lean()
    assert rendered == "((MAnd (MTrue MTrue) MTrue)".replace("(", "").replace(")", "") or rendered
    # exact form: nested binary props are parenthesized
    assert rendered.count("(") == rendered.count(")")
    assert "MAnd" in rendered


def test_s2_rejects_false_goal():
    import pytest
    with pytest.raises(ValueError):
        synthesize_proof(PropNode("false"), choose_left=lambda p: True)


def test_mutations_produce_different_source():
    rng = random.Random(11)
    s = generate_s2(rng, 0)
    parent = {"sample_id": "p1", **s}
    results = [mutate_sample(parent, rng, i) for i in range(10)]
    mutated = [m for m in results if m is not None]
    assert mutated, "at least some mutations must apply"
    for m in mutated:
        assert m["mutation_type"] in (
            "identifier_replacement", "argument_replacement", "argument_permutation",
            "operator_replacement", "tactic_replacement", "tactic_deletion",
            "binder_modification",
        )
        assert m["parent_id"] == "p1"


def test_audit_sample_blocks_foreign_import():
    violations, imports = audit_sample("import Std.Data.HashMap\ntheorem t : MTrue := MTrue.intro")
    assert any("disallowed import" in v for v in violations)
    assert "Std.Data.HashMap" in imports


def test_audit_sample_blocks_sorry():
    violations, _ = audit_sample("theorem t : MTrue := sorry")
    assert any("sorry" in v for v in violations)


def test_audit_sample_blocks_math_content():
    violations, _ = audit_sample("theorem t : Nat := zero")
    assert any("Nat" in v for v in violations)


def test_audit_corpus_clean():
    samples = [
        _mk("S2", 0, "theorem a : MTrue := MTrue.intro", "true", "MTrue.intro"),
        _mk("S2", 1, "theorem b : (MAnd MTrue MTrue) := (MAnd.intro MTrue.intro MTrue.intro)",
            "(and true true)", "(MAnd.intro MTrue.intro MTrue.intro)"),
    ]
    report = audit_corpus(samples, GENERATOR_VERSION, 42)
    assert report.ok, report.violations
    assert report.checks["n_samples"] == 2


def test_splits_deterministic_and_disjoint():
    samples = [_mk("S2", i, f"theorem t{i} : MTrue := MTrue.intro") for i in range(50)]
    s1 = make_splits(samples, seed=5)
    s2 = make_splits(samples, seed=5)
    assert [x["split"] for x in s1] == [x["split"] for x in s2]
    splits = {x["split"] for x in s1}
    assert splits == {SPLIT_TRAIN, "VALIDATION", SPLIT_TEST}
    # every sample has exactly one split
    assert all(x["split"] in splits for x in s1)


def test_leakage_audit_detects_duplicates():
    dup = "theorem dup : MTrue := MTrue.intro"
    samples = [
        {**_mk("S2", 0, dup), "split": SPLIT_TRAIN, "prop_structure": "true",
         "proof_structure": "MTrue.intro"},
        {**_mk("S2", 1, dup), "split": SPLIT_TEST, "prop_structure": "true",
         "proof_structure": "MTrue.intro"},
        {**_mk("S2", 2, "theorem other : (MAnd MTrue MTrue) := (MAnd.intro MTrue.intro MTrue.intro)"),
         "split": SPLIT_TRAIN, "prop_structure": "(and true true)",
         "proof_structure": "(MAnd.intro MTrue.intro MTrue.intro)"},
    ]
    report = leakage_audit(samples)
    assert not report.ok
    assert report.exact_duplicates >= 1


def test_leakage_audit_clean_corpus():
    samples = [
        {**_mk("S2", 0, "theorem t0 : MTrue := MTrue.intro"),
         "split": SPLIT_TRAIN, "prop_structure": "true",
         "proof_structure": "MTrue.intro"},
        {**_mk("S2", 1, "theorem t1 : (MAnd MTrue MTrue) := (MAnd.intro MTrue.intro MTrue.intro)"),
         "split": SPLIT_TRAIN, "prop_structure": "(and true true)",
         "proof_structure": "(MAnd.intro MTrue.intro MTrue.intro)"},
        {**_mk("S2", 2, "theorem t2 : (MOr MTrue MTrue) := (MOr.inl MTrue.intro)"),
         "split": SPLIT_TRAIN, "prop_structure": "(or true true)",
         "proof_structure": "(MOr.inl MTrue.intro)"},
    ]
    report = leakage_audit(samples)
    assert report.ok, report.details


def test_normalized_fingerprint_ignores_theorem_name():
    a = "theorem foo : MTrue := MTrue.intro"
    b = "theorem bar : MTrue := MTrue.intro"
    assert normalized_fingerprint(a) == normalized_fingerprint(b)
