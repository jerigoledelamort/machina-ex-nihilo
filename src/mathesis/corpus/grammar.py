"""Grammar of the allowed generation subset (spec sections 20-21).

The subset is intentionally minimal and structural: propositional structure
over the fixed inductive types of Mathesis.Basic. No mathematical theories
(Nat arithmetic, groups, calculus, ...) are encoded - section 21 boundary.

S2 uses constructor signatures (type information from the environment) to
synthesize type-correct proof terms. This is explicitly a use of the trusted
computational substrate (section 20) and is classified as such.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

GENERATOR_VERSION = "0.2.0"

# Constructor signatures (from Mathesis.Basic). Used by the S2 type-aware
# synthesizer. These mirror the environment; the Auditor cross-checks them
# against the Lean environment via #check.
CONSTRUCTOR_SIGNATURES: dict[str, str] = {
    "MTrue.intro": "MTrue",
    "MAnd.intro": "∀ (a b : Prop), a → b → MAnd a b",
    "MOr.inl": "∀ (a b : Prop), a → MOr a b",
    "MOr.inr": "∀ (a b : Prop), b → MOr a b",
}


@dataclass(frozen=True)
class PropNode:
    """Proposition AST: leaf or binary connective."""

    op: str                    # "true" | "and" | "or"
    left: Optional["PropNode"] = None
    right: Optional["PropNode"] = None

    def to_lean(self) -> str:
        if self.op == "true":
            return "MTrue"
        if self.op == "false":
            return "MFalse"
        l = self.left.to_lean() if self.left else ""
        r = self.right.to_lean() if self.right else ""
        head = "MAnd" if self.op == "and" else "MOr"
        # nested binary props need explicit parentheses: MAnd is a curried
        # constructor application, `MAnd A B C D` would misparse
        return f"({head} {l} {r})"

    def structure_key(self) -> str:
        """Normalized structure used for duplicate detection (s27)."""
        if self.op in ("true", "false"):
            return self.op
        return f"({self.op} {self.left.structure_key()} {self.right.structure_key()})"


@dataclass(frozen=True)
class ProofNode:
    """Proof term AST over the subset constructors."""

    head: str                   # constructor name
    args: tuple["ProofNode", ...] = ()

    def to_lean(self) -> str:
        if not self.args:
            return self.head
        return f"({self.head} {' '.join(a.to_lean() for a in self.args)})"

    def structure_key(self) -> str:
        if not self.args:
            return self.head
        return f"({self.head} {' '.join(a.structure_key() for a in self.args)})"


def prop_type(node: PropNode) -> str:
    """Rendered Lean type of a proposition node."""
    return node.to_lean()


def synthesize_proof(prop: PropNode, choose_left: callable) -> ProofNode:
    """Type-aware proof synthesis (S2 core).

    Builds a proof term for `prop` by structural induction using the
    constructor signatures. `choose_left(prop)` decides inl/inr for MOr.
    """
    if prop.op == "true":
        return ProofNode("MTrue.intro")
    if prop.op == "false":
        # MFalse has no constructor; uninhabited. Never synthesized as goal.
        raise ValueError("cannot synthesize proof for MFalse")
    if prop.op == "and":
        return ProofNode(
            "MAnd.intro",
            (synthesize_proof(prop.left, choose_left), synthesize_proof(prop.right, choose_left)),
        )
    if prop.op == "or":
        use_left = choose_left(prop)
        sub = synthesize_proof(prop.left if use_left else prop.right, choose_left)
        return ProofNode("MOr.inl" if use_left else "MOr.inr", (sub,))
    raise ValueError(f"unknown prop op: {prop.op}")
