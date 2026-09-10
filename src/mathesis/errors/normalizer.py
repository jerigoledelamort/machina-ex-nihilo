"""Error normalization (spec section 29).

Lean errors are not fed to the model as raw text. Normalized representation:
  error_type, location, expected_type, actual_type, message, hint
If a specific error cannot be reliably structured, raw_message is the fallback.

The Lean version is part of experiment metadata (section 29).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from ..validation.statuses import Diagnostic


@dataclass
class NormalizedError:
    error_type: str
    location: Optional[dict] = None          # {"line": int, "column": int}
    expected_type: Optional[str] = None
    actual_type: Optional[str] = None
    message: str = ""
    hint: str = ""
    raw_message: str = ""                    # fallback, always preserved

    def to_dict(self) -> dict:
        return {
            "error_type": self.error_type,
            "location": self.location,
            "expected_type": self.expected_type,
            "actual_type": self.actual_type,
            "message": self.message,
            "hint": self.hint,
            # raw_message kept as fallback (s29)
            "raw_message": self.raw_message,
        }


# error_type -> detection patterns (order matters: first match wins)
_ERROR_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("type_mismatch", re.compile(r"type mismatch|application type mismatch", re.IGNORECASE)),
    ("definitional_equality", re.compile(r"not a definitional equality", re.IGNORECASE)),
    ("unknown_identifier", re.compile(r"unknown identifier", re.IGNORECASE)),
    ("unknown_constant", re.compile(r"unknown constant", re.IGNORECASE)),
    ("unknown_variable", re.compile(r"unknown variable", re.IGNORECASE)),
    ("synthesis_failure", re.compile(r"failed to synthesize", re.IGNORECASE)),
    ("function_expected", re.compile(r"function expected", re.IGNORECASE)),
    ("invalid_field", re.compile(r"invalid field notation", re.IGNORECASE)),
    ("parse_error", re.compile(r"expected token|unexpected token|invalid character", re.IGNORECASE)),
    ("unsolved_goals", re.compile(r"unsolved goals", re.IGNORECASE)),
    ("arity_error", re.compile(r"function expected at|has been used in", re.IGNORECASE)),
]


def classify_error_type(message: str) -> str:
    for error_type, pattern in _ERROR_PATTERNS:
        if pattern.search(message):
            return error_type
    return "unclassified"


_EXPECTED_ACTUAL = re.compile(
    r"(?:has type|term)\s*\n?\s*(?P<actual>.+?)\s*\n"
    r".*?(?:but is expected to have type|but expected to have type)\s*\n?\s*(?P<expected>.+)",
    re.DOTALL,
)
_SIMPLE_EXPECTED_ACTUAL = re.compile(
    r"type mismatch\s*\n\s*(?P<actual>.+?)\s*\nhas type\s*\n\s*(?P<actual_type>.+?)\s*\n"
    r"but is expected to have type\s*\n\s*(?P<expected_type>.+)",
    re.DOTALL,
)
_HINT = re.compile(r"Hint:\s*(.+)", re.DOTALL)


def normalize_diagnostic(d: Diagnostic) -> NormalizedError:
    """Normalize one diagnostic (section 29). raw_message is always kept."""
    message = d.message or ""
    error_type = classify_error_type(message)

    location = None
    if d.line is not None:
        location = {"line": d.line, "column": d.column}

    expected = actual = None
    m = _SIMPLE_EXPECTED_ACTUAL.search(message)
    if m:
        actual = m.group("actual_type").strip()
        expected = m.group("expected_type").strip()
    else:
        m2 = _EXPECTED_ACTUAL.search(message)
        if m2:
            actual = m2.group("actual").strip()
            expected = m2.group("expected").strip()

    hint = ""
    mh = _HINT.search(message)
    if mh:
        hint = mh.group(1).strip()

    # first line = concise message
    concise = message.splitlines()[0].strip() if message else ""

    return NormalizedError(
        error_type=error_type,
        location=location,
        expected_type=expected,
        actual_type=actual,
        message=concise,
        hint=hint,
        raw_message=message,
    )


def normalize_diagnostics(diags: list[Diagnostic]) -> list[NormalizedError]:
    return [normalize_diagnostic(d) for d in diags]
