"""Deterministic benchmark source generator (spec sections 16-17, 19).

Programmatic, seed-controlled, non-LLM. Uses only the minimal environment
structures (MTrue/MAnd/MOr) - no human-authored mathematical theory (s21).
"""

from __future__ import annotations

# PATTERNS[i] and PROOFS[i] are type-aligned pairs (verified by batch tests).
PATTERNS = [
    "MTrue",
    "MAnd MTrue MTrue",
    "MOr MTrue MTrue",
    "MAnd MTrue (MOr MTrue MTrue)",
    "MOr (MAnd MTrue MTrue) MTrue",
    "MAnd (MOr MTrue MTrue) (MAnd MTrue MTrue)",
]

PROOFS = [
    "MTrue.intro",
    "MAnd.intro MTrue.intro MTrue.intro",
    "MOr.inl MTrue.intro",
    "MAnd.intro MTrue.intro (MOr.inl MTrue.intro)",
    "MOr.inl (MAnd.intro MTrue.intro MTrue.intro)",
    "MAnd.intro (MOr.inl MTrue.intro) (MAnd.intro MTrue.intro MTrue.intro)",
]

TACTIC_PROOFS = [
    "by exact MTrue.intro",
    "by exact MAnd.intro MTrue.intro MTrue.intro",
    "by exact MOr.inl MTrue.intro",
    "by trivial",
]

HEADER = "import Mathesis.Basic"


def generate_theorem(index: int) -> str:
    """Deterministic theorem by index; every 10th uses tactic mode.

    Tactic-mode theorems reuse the aligned PATTERNS/PROOFS pairs via
    `by exact`, guaranteeing type correctness.
    """
    if index % 10 == 9:
        k = index % len(PATTERNS)
        return f"theorem bench_t{index} : {PATTERNS[k]} := by exact {PROOFS[k]}"
    prop = PATTERNS[index % len(PATTERNS)]
    proof = PROOFS[index % len(PROOFS)]
    return f"theorem bench_t{index} : {prop} := {proof}"


def generate_source(n_theorems: int, *, seed: int = 0) -> str:
    """Deterministic benchmark file with n_theorems theorems."""
    lines = [HEADER]
    for i in range(n_theorems):
        lines.append(generate_theorem((i + seed * 7919) % 1000003))
    return "\n".join(lines) + "\n"


def generate_action_sequence(n_actions: int, *, seed: int = 0) -> list[str]:
    """Realistic sequential action stream (s17): declarations building on each
    other plus occasional corrections (error -> fix), not an artificial
    rfl-loop."""
    actions: list[str] = []
    for i in range(n_actions):
        kind = i % 6
        if kind == 0:
            actions.append(f"def bench_chain{i} : MUnit := MUnit.mk")
        elif kind == 1:
            # intentional error first (realistic correction scenario)
            actions.append(f"theorem bench_c{i} : MTrue := MAnd.intro MTrue.intro MTrue.intro")
        elif kind == 2:
            # corrected version
            actions.append(f"theorem bench_c{i} : MTrue := MTrue.intro")
        elif kind == 3:
            actions.append(f"theorem bench_d{i} : MAnd MTrue MTrue := MAnd.intro MTrue.intro MTrue.intro")
        elif kind == 4:
            # bench_chain{i-4} was created by the kind==0 action at i-4
            actions.append(f"#check bench_chain{i - 4}")
        else:
            actions.append(f"theorem bench_e{i} : MOr MTrue (MAnd MTrue MTrue) := MOr.inl MTrue.intro")
    return actions
