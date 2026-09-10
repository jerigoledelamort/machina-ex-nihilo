"""Corpus Auditor (spec section 22).

Audits: generator source, generated corpus, imports, dependencies,
mathematical constants/rules, human-authored content, forbidden declarations.
Produces a machine-readable report.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..validation.safety import extract_imports, strip_comments_and_strings


def _strip_python(text: str) -> str:
    """Remove Python comments and string literals (incl. docstrings).

    Character-level scanner: avoids regex escaping pitfalls entirely.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == "#" and (not out or out[-1] != "'") :
            # comment to end of line (conservative: '#' inside strings already consumed)
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == '"' and nxt == '"' or ch == "'" and nxt == "'":
            quote = ch * 3
            j = text.find(quote, i + 3)
            if j == -1:
                i = n
            else:
                i = j + 3
            out.append(" ")
            continue
        if ch in ('"', "'"):
            j = i + 1
            while j < n and text[j] != ch and text[j] != "\n":
                j += 1
            i = j + 1
            out.append(" ")
            continue
        out.append(ch)
        i += 1
    return "".join(out)

# Mathematical constants / operators that must NOT appear in generated corpus
# (section 21: no hand-coded mathematical theories).
_MATH_PATTERNS = [
    r"\bNat\b", r"\bInt\b", r"\bReal\b", r"\bList\b", r"\bArray\b",
    r"\bGroup\b", r"\bRing\b", r"\bField\b",
    r"[+\-*/^%]",  # arithmetic operators
    r"\bzero\b", r"\bsucc\b", r"\bplus\b", r"\bmult\b",
    r"\bleanlab\b",
]

# Human-authored content markers: corpus must be generator-produced only.
_HUMAN_MARKERS = [
    "sorry", "admit", "native_decide", "unsafe",
]

_FORBIDDEN_DECLS = ["axiom", "opaque", "macro_rules", "set_option", "elab", "syntax"]


@dataclass
class AuditReport:
    ok: bool
    checks: dict = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "checks": self.checks, "violations": list(self.violations)}


def audit_generator_source(generator_files: list[Path]) -> AuditReport:
    """Static audit of the generator's own source code (section 22)."""
    violations: list[str] = []
    for path in generator_files:
        if not path.exists():
            violations.append(f"generator file missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        cleaned = _strip_python(text)
        for decl in _FORBIDDEN_DECLS:
            if re.search(rf"\b{decl}\b", cleaned):
                violations.append(f"{path.name}: forbidden declaration '{decl}'")
        for marker in _HUMAN_MARKERS:
            if re.search(rf"\b{marker}\b", cleaned):
                violations.append(f"{path.name}: forbidden marker '{marker}'")
    return AuditReport(
        ok=not violations,
        checks={"files_audited": [p.name for p in generator_files]},
        violations=violations,
    )


def audit_sample(source: str) -> tuple[list[str], list[str]]:
    """Audit one generated sample: returns (violations, imports)."""
    violations: list[str] = []
    cleaned = strip_comments_and_strings(source)

    imports = extract_imports(source)
    for module in imports:
        if not (module == "Mathesis" or module.startswith("Mathesis.")):
            violations.append(f"disallowed import '{module}'")

    for marker in _HUMAN_MARKERS:
        if re.search(rf"\b{marker}\b", cleaned):
            violations.append(f"forbidden marker '{marker}'")

    for decl in _FORBIDDEN_DECLS:
        if re.search(rf"\b{decl}\b", cleaned):
            violations.append(f"forbidden declaration '{decl}'")

    for pattern in _MATH_PATTERNS:
        if re.search(pattern, cleaned):
            violations.append(f"mathematical content pattern '{pattern}'")

    return violations, imports


def audit_corpus(samples: list[dict], generator_version: str, seed: int) -> AuditReport:
    """Full corpus audit with machine-readable summary (section 22)."""
    violations: list[str] = []
    level_counts: dict[str, int] = {}
    mutation_counts: dict[str, int] = {}
    imports_seen: set[str] = set()

    for s in samples:
        source = s.get("source", "")
        sample_violations, imports = audit_sample(source)
        imports_seen.update(imports)
        for v in sample_violations:
            violations.append(f"{s.get('sample_id', '?')}: {v}")
        level = s.get("level", "?")
        level_counts[level] = level_counts.get(level, 0) + 1
        if s.get("mutation_type"):
            mt = s["mutation_type"]
            mutation_counts[mt] = mutation_counts.get(mt, 0) + 1

    report = AuditReport(
        ok=not violations,
        checks={
            "n_samples": len(samples),
            "generator_version": generator_version,
            "seed": seed,
            "level_counts": level_counts,
            "mutation_counts": mutation_counts,
            "imports_seen": sorted(imports_seen),
            "all_imports_allowed": all(
                i == "Mathesis" or i.startswith("Mathesis.") for i in imports_seen
            ),
        },
        violations=violations,
    )
    return report


def audit_report_hash(report: AuditReport) -> str:
    return hashlib.sha256(
        json.dumps(report.to_dict(), sort_keys=True).encode("utf-8")
    ).hexdigest()
