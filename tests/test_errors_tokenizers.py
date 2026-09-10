"""Tests for error normalization (s29) and tokenizers (s28-s30)."""

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from mathesis.errors import normalize_diagnostic  # noqa: E402
from mathesis.tokenizers import LeanTokenizer  # noqa: E402
from mathesis.validation.statuses import Diagnostic  # noqa: E402


def _diag(message: str, line=1, col=0) -> Diagnostic:
    return Diagnostic(severity="error", line=line, column=col, message=message)


def test_type_mismatch_structured():
    ne = normalize_diagnostic(_diag(
        "Type mismatch\n  rfl\nhas type\n  ?m.8 = ?m.8\n"
        "but is expected to have type\n  1 = 2"
    ))
    assert ne.error_type == "type_mismatch"
    assert ne.expected_type == "1 = 2"
    assert ne.actual_type == "?m.8 = ?m.8"
    assert ne.raw_message  # fallback always preserved (s29)
    assert ne.location == {"line": 1, "column": 0}


def test_unknown_identifier():
    ne = normalize_diagnostic(_diag("unknown identifier 'MAndx'"))
    assert ne.error_type == "unknown_identifier"
    assert ne.message == "unknown identifier 'MAndx'"


def test_application_type_mismatch():
    ne = normalize_diagnostic(_diag(
        "Application type mismatch: The argument\n  MAnd MTrue\nhas type\n  Prop → Prop\n"
        "but is expected to have type\n  Prop\nin the application\n  MOr (MAnd MTrue)"
    ))
    assert ne.error_type == "type_mismatch"
    assert ne.actual_type is not None and ne.expected_type is not None


def test_parse_error_classification():
    ne = normalize_diagnostic(_diag("expected token"))
    assert ne.error_type == "parse_error"


def test_unclassified_falls_back():
    ne = normalize_diagnostic(_diag("something completely unusual happened"))
    assert ne.error_type == "unclassified"
    assert ne.raw_message == "something completely unusual happened"


def test_hint_extracted():
    ne = normalize_diagnostic(_diag(
        "Function expected at\n  MAnd\nHint: The identifier `MAnd` is unknown"
    ))
    assert "autoImplicit" in ne.hint or "unknown" in ne.hint


def test_lean_tokenizer_roundtrip_words():
    tok = LeanTokenizer()
    toks = tok.tokenize("theorem t1 : MTrue := MTrue.intro")
    assert "theorem" in toks and "MTrue.intro" in toks and ":=" in toks
    # identifiers stay atomic (Lean-aware property)
    assert "MTrue.intro" in toks


def test_lean_tokenizer_proof_state_tags():
    tok = LeanTokenizer()
    toks = tok.tokenize("<GOAL> MTrue <ACTION> exact MTrue.intro")
    for tag in ("<GOAL>", "<ACTION>"):
        assert tag in toks


def test_lean_tokenizer_deterministic():
    tok = LeanTokenizer()
    text = "theorem t : (MAnd MTrue MTrue) := (MAnd.intro MTrue.intro MTrue.intro)"
    assert tok.tokenize(text) == tok.tokenize(text)


def test_lean_tokenizer_unknown_chars_no_crash():
    tok = LeanTokenizer()
    toks = tok.tokenize("theorem weird € £ ∅ : MTrue := trivial")
    assert len(toks) > 0


def test_lean_tokenizer_vocab_size():
    tok = LeanTokenizer()
    assert tok.vocab_size > 50  # tags + keywords + operators + base specials
