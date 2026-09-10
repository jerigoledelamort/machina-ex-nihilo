"""Corpus generator S0/S1/S2 + mutation-based plausible errors (s19-s24).

Deterministic, seed-controlled, versioned, programmatic, non-LLM (s19).
Levels (s20):
  S0 - surface syntax generation (valid syntax, random semantics)
  S1 - syntax-aware AST generation (valid structure, types may mismatch)
  S2 - type-aware generation using constructor type information
       (explicit use of the trusted computational substrate, s20)
Negative examples are produced predominantly by mutation of valid samples
(s24); random garbage is not the main source.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .grammar import (
    GENERATOR_VERSION,
    PropNode,
    ProofNode,
    synthesize_proof,
)


def _random_prop(rng: random.Random, depth: int, allow_false: bool = False) -> PropNode:
    """Random proposition tree with bounded depth."""
    if depth <= 0:
        if allow_false and rng.random() < 0.15:
            return PropNode("false")
        return PropNode("true")
    op = rng.choice(["and", "or", "true"])
    if op == "true":
        return PropNode("true")
    return PropNode(
        op,
        left=_random_prop(rng, depth - 1, allow_false),
        right=_random_prop(rng, depth - 1, allow_false),
    )


def _random_proof(rng: random.Random, depth: int) -> ProofNode:
    """Random proof tree (S1): syntactically valid, type-unchecked."""
    if depth <= 0:
        return ProofNode("MTrue.intro")
    head = rng.choice(["MTrue.intro", "MAnd.intro", "MOr.inl", "MOr.inr"])
    if head == "MTrue.intro":
        return ProofNode(head)
    n_args = 2 if head == "MAnd.intro" else 1
    return ProofNode(head, tuple(_random_proof(rng, depth - 1) for _ in range(n_args)))


# --------------------------------------------------------------------- #
# S0: surface syntax
# --------------------------------------------------------------------- #

_S0_PROP_FRAGMENTS = [
    "MTrue", "MFalse", "MAnd MTrue MTrue", "MOr MFalse MTrue",
    "MAnd (MOr MTrue MFalse) MTrue", "MOr MTrue (MAnd MTrue MFalse)",
    "MAnd MTrue",              # arity error (surface-level)
    "MOr (MAnd MTrue)",        # arity error
]
_S0_PROOF_FRAGMENTS = [
    "MTrue.intro", "MAnd.intro MTrue.intro MTrue.intro",
    "MOr.inl MTrue.intro", "MOr.inr MTrue.intro",
    "MAnd.intro MTrue.intro",  # arity error
    "by exact MTrue.intro", "by exact MAnd.intro MTrue.intro MTrue.intro",
]


def generate_s0(rng: random.Random, index: int) -> dict:
    """S0: surface-level template generation; often semantically invalid."""
    prop = rng.choice(_S0_PROP_FRAGMENTS)
    proof = rng.choice(_S0_PROOF_FRAGMENTS)
    source = f"theorem s0_t{index} : {prop} := {proof}"
    return {
        "source": source,
        "level": "S0",
        "prop_structure": None,
        "proof_structure": None,
    }


# --------------------------------------------------------------------- #
# S1: syntax-aware AST generation
# --------------------------------------------------------------------- #

def generate_s1(rng: random.Random, index: int) -> dict:
    """S1: AST-level generation; structure valid, types may mismatch."""
    prop = _random_prop(rng, depth=rng.randint(1, 3), allow_false=True)
    proof = _random_proof(rng, depth=rng.randint(0, 3))
    source = f"theorem s1_t{index} : {prop.to_lean()} := {proof.to_lean()}"
    return {
        "source": source,
        "level": "S1",
        "prop_structure": prop.structure_key(),
        "proof_structure": proof.structure_key(),
    }


# --------------------------------------------------------------------- #
# S2: type-aware generation
# --------------------------------------------------------------------- #

def generate_s2(rng: random.Random, index: int) -> dict:
    """S2: type-aware synthesis - proof term matches the proposition by
    construction (using constructor type information; s20 substrate use)."""
    prop = _random_prop(rng, depth=rng.randint(1, 3))
    proof = synthesize_proof(
        prop, choose_left=lambda _p: rng.random() < 0.5
    )
    source = f"theorem s2_t{index} : {prop.to_lean()} := {proof.to_lean()}"
    return {
        "source": source,
        "level": "S2",
        "prop_lean": prop.to_lean(),
        "proof_lean": proof.to_lean(),
        "prop_structure": prop.structure_key(),
        "proof_structure": proof.structure_key(),
    }


GENERATORS = {"S0": generate_s0, "S1": generate_s1, "S2": generate_s2}


# --------------------------------------------------------------------- #
# Mutation-based plausible errors (s24)
# --------------------------------------------------------------------- #

MUTATION_TYPES = [
    "identifier_replacement",
    "argument_replacement",
    "argument_permutation",
    "operator_replacement",
    "tactic_replacement",
    "tactic_deletion",
    "binder_modification",
]


def _replace_identifiers(text: str, rng: random.Random) -> str:
    """identifier replacement: swap subset constructors/constants."""
    replacements = {
        "MTrue": rng.choice(["MFalse", "MAnd", "MOr"]),
        "MAnd": rng.choice(["MOr", "MTrue"]),
        "MOr": rng.choice(["MAnd", "MTrue"]),
        "MTrue.intro": rng.choice(["MAnd.intro", "MOr.inl"]),
        "MAnd.intro": rng.choice(["MOr.inl", "MTrue.intro"]),
        "MOr.inl": rng.choice(["MOr.inr", "MAnd.intro"]),
    }
    for old, new in replacements.items():
        if old in text and rng.random() < 0.6:
            return text.replace(old, new, 1)
    return text


def _mutate_tree(prop: PropNode, rng: random.Random) -> PropNode:
    """operator replacement / argument modification on the prop AST."""
    if prop.op in ("true", "false"):
        if rng.random() < 0.5:
            return PropNode("false" if prop.op == "true" else "true")
        return prop
    if rng.random() < 0.4:
        # operator replacement: and <-> or
        return PropNode(
            "or" if prop.op == "and" else "and", prop.left, prop.right
        )
    if rng.random() < 0.5:
        # argument permutation
        return PropNode(prop.op, prop.right, prop.left)
    return PropNode(
        prop.op,
        _mutate_tree(prop.left, rng) if prop.left else None,
        _mutate_tree(prop.right, rng) if prop.right else None,
    )


def mutate_sample(sample: dict, rng: random.Random, index: int) -> Optional[dict]:
    """Apply one mutation to a (usually S2) sample; returns mutated sample.

    Returns None if the mutation is not applicable. The mutation type is
    recorded (s24); the mutated sample is NOT assumed invalid - Lean decides.
    """
    level = sample["level"]
    source = sample["source"]

    if level == "S2" and sample.get("prop_structure"):
        # AST-level mutations for typed samples
        prop = _parse_structure(sample["prop_structure"])
        if prop is None:
            return None
        mutated = _mutate_tree(prop, rng)
        # keep the original proof: after operator mutation it will usually
        # mismatch -> plausible error
        source = f"theorem s2_m{index} : {mutated.to_lean()} := {sample['proof_lean']}"
        return {
            "source": source,
            "level": "S2",
            "prop_structure": mutated.structure_key(),
            "proof_structure": sample["proof_structure"],
            "mutation_type": "operator_replacement"
            if mutated.op != prop.op else "argument_permutation",
            "parent_id": sample.get("sample_id"),
        }

    # text-level mutations for S0/S1
    kind = rng.choice(["identifier_replacement", "tactic_replacement", "tactic_deletion"])
    if kind == "identifier_replacement":
        mutated = _replace_identifiers(source, rng)
        if mutated == source:
            return None
        return {"source": mutated, "level": level, "prop_structure": sample.get("prop_structure"),
                "proof_structure": sample.get("proof_structure"),
                "mutation_type": "identifier_replacement", "parent_id": sample.get("sample_id")}
    if kind == "tactic_replacement" and "by exact" in source:
        mutated = source.replace("by exact", "by apply", 1)
        return {"source": mutated, "level": level, "prop_structure": sample.get("prop_structure"),
                "proof_structure": sample.get("proof_structure"),
                "mutation_type": "tactic_replacement", "parent_id": sample.get("sample_id")}
    if kind == "tactic_deletion" and "by exact " in source:
        mutated = source.replace("by exact ", "by ", 1)
        return {"source": mutated, "level": level, "prop_structure": sample.get("prop_structure"),
                "proof_structure": sample.get("proof_structure"),
                "mutation_type": "tactic_deletion", "parent_id": sample.get("sample_id")}
    return None


def _parse_structure(key: str) -> Optional[PropNode]:
    """Parse a structure_key back into a PropNode."""
    key = key.strip()
    if key == "true":
        return PropNode("true")
    if key == "false":
        return PropNode("false")
    if key.startswith("(") and key.endswith(")"):
        inner = key[1:-1]
        for op in ("and", "or"):
            prefix = f"{op} "
            if inner.startswith(prefix):
                rest = inner[len(prefix):]
                left, right = _split_top(rest)
                if left is None:
                    continue
                return PropNode(op, _parse_structure(left), _parse_structure(right))
    return None


def _split_top(text: str) -> tuple[Optional[str], Optional[str]]:
    """Split 'L R' at top level (parenthesis-aware)."""
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == " " and depth == 0:
            return text[:i], text[i + 1:]
    return None, None
