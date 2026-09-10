"""Safety validation and trusted-base inspection (spec sections 9, 10, 65).

Generated Lean code is untrusted input. Before elaboration the source is
scanned for forbidden constructs:
  sorry / admit / unsafe / native_decide / user-defined axioms / etc.

`native_decide` is NOT equivalent to ordinary kernel reduction; if it were
ever allowed in a special research pipeline it would have to be recorded in
provenance. In the Milestone 1 proof pipeline it is forbidden outright.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SafetyReport:
    ok: bool
    violations: list[str] = field(default_factory=list)
    restricted_uses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "violations": list(self.violations),
            "restricted_uses": list(self.restricted_uses),
        }


_LEAN_COMMENT = re.compile(r"/-.*?(-/|$)", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_LEAN_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.!]*")


def strip_comments_and_strings(source: str) -> str:
    """Remove comments and string literals so token scans don't false-positive."""
    source = _LEAN_COMMENT.sub(" ", source)
    source = _LINE_COMMENT.sub(" ", source)
    source = _LEAN_STRING.sub('""', source)
    return source


def _iter_words(source: str):
    for match in _WORD.finditer(source):
        yield match.group(0), match.start()


def scan_safety(source: str, *, forbidden_tokens, forbidden_declarations, restricted_patterns) -> SafetyReport:
    """Scan raw Lean source for forbidden constructs (pre-elaboration)."""
    cleaned = strip_comments_and_strings(source)
    violations: list[str] = []
    restricted: list[str] = []

    lowered_words = {w.lower(): w for w, _ in _iter_words(cleaned)}
    positions = {w.lower(): pos for w, pos in _iter_words(cleaned)}

    for token in forbidden_tokens:
        key = token.lower()
        if key in lowered_words:
            violations.append(
                f"forbidden token '{token}' at offset {positions[key]}"
            )

    for decl in forbidden_declarations:
        key = decl.lower()
        if key in lowered_words:
            # `axiom`, `opaque`, `elab`, ... appear as declaration keywords
            violations.append(
                f"forbidden declaration/keyword '{decl}' at offset {positions[key]}"
            )

    for pattern in restricted_patterns:
        if pattern in cleaned:
            restricted.append(pattern)
            violations.append(f"restricted pattern '{pattern}' used")

    return SafetyReport(ok=not violations, violations=violations, restricted_uses=restricted)


_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)", re.MULTILINE)


def extract_imports(source: str) -> list[str]:
    """Extract the import list of a Lean file (spec section 11)."""
    return _IMPORT_RE.findall(source)


def validate_imports(source: str, *, allowed_prefixes) -> list[str]:
    """Return violations: any import outside the allowed minimal environment."""
    violations = []
    for module in extract_imports(source):
        if not any(module == p or module.startswith(p + ".") for p in allowed_prefixes):
            violations.append(f"disallowed import '{module}'")
    return violations


# Standard Lean axioms reported by `#print axioms` that belong to the
# kernel-level trusted base (section 9). Everything else (e.g. sorryAx)
# is a violation.
TRUSTED_KERNEL_AXIOMS = {"Classical.choice", "propext", "Quot.sound"}

_PRINT_AXIOMS_RE = re.compile(r"'([^']+)' depends on axioms:\s*\[([^\]]*)\]")
_AXIOM_ITEM_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*")


def parse_print_axioms(output: str) -> dict[str, list[str]]:
    """Parse `#print axioms` output: {declaration: [axiom names]}."""
    result: dict[str, list[str]] = {}
    for decl, axioms in _PRINT_AXIOMS_RE.findall(output):
        result[decl] = _AXIOM_ITEM_RE.findall(axioms)
    return result


def inspect_trusted_base(axiom_deps: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """Split axiom dependencies into (trusted kernel principles, violations).

    sorryAx here indicates a proof slipped past the safety scan - hard violation.
    """
    trusted: list[str] = []
    violations: list[str] = []
    for decl, axioms in axiom_deps.items():
        for ax in axioms:
            if ax in TRUSTED_KERNEL_AXIOMS:
                if ax not in trusted:
                    trusted.append(ax)
            else:
                violations.append(f"'{decl}' depends on non-trusted axiom '{ax}'")
    return trusted, violations
