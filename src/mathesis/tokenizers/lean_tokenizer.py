"""Lean-aware tokenizer (spec sections 28-30).

Handles: Lean syntax, identifiers, operators, numerals, tactics, proof-state
tags (<GOAL>, <CONTEXT>, <STATE>, <ERROR>, <HISTORY>, <ACTION> - section 31),
normalized errors. Deterministic, no training required.
"""

from __future__ import annotations

import re
from typing import Iterable

PROOF_STATE_TAGS = [
    "<GOAL>", "<CONTEXT>", "<STATE>", "<ERROR>", "<HISTORY>", "<ACTION>",
    "<GOAL_END>", "<PAD>", "<BOS>", "<EOS>",
]

_LEAN_KEYWORDS = [
    "theorem", "def", "inductive", "structure", "instance", "example",
    "abbrev", "axiom", "by", "exact", "intro", "apply", "rfl", "simp",
    "constructor", "cases", "induction", "assumption", "refine", "obtain",
    "have", "let", "show", "calc", "fun", "forall", "exists", "from",
    "where", "with", "at", "in", "do", "return", "if", "then", "else",
    "match", "true", "false", "And", "Or", "Not", "Eq", "Iff",
]

# Multi-char operators first (longest match wins)
_OPERATORS = [
    ":=", "->", "→", "←", "↔", "∧", "∨", "¬", "∀", "∃", "λ", "×",
    "<|>", "|>", "<;", ">",
    "(", ")", "[", "]", "{", "}", ":", ";", ",", ".", "|", "=", "<>", "≠",
]

_TOKEN_RE = re.compile(
    r"|".join(re.escape(t) for t in PROOF_STATE_TAGS)
    + r"|[A-Za-z_\u0370-\u03ff][A-Za-z0-9_\u0370-\u03ff.!?'⟨⟩]*"
    + r"|\d+"
    + r"|" + "|".join(re.escape(op) for op in sorted(_OPERATORS, key=len, reverse=True))
    + r"|\s+"
    + r"|."
)


class LeanTokenizer:
    """Deterministic vocabulary-based tokenizer with char fallback."""

    def __init__(self):
        # vocabulary: special tags + keywords + operators + single chars
        self.itos: list[str] = ["<PAD>", "<BOS>", "<EOS>", "<UNK>"]
        self.itos.extend(PROOF_STATE_TAGS)
        self.itos.extend(_LEAN_KEYWORDS)
        self.itos.extend(_OPERATORS)
        self.stoi: dict[str, int] = {t: i for i, t in enumerate(self.itos)}
        self._word_re = re.compile(
            r"|".join(re.escape(t) for t in PROOF_STATE_TAGS)
            + r"|[A-Za-z_\u0370-\u03ff][A-Za-z0-9_\u0370-\u03ff.!?'⟨⟩]*"
            + r"|\d+"
        )

    @property
    def vocab_size(self) -> int:
        return len(self.itos)

    def _known_word(self, w: str) -> bool:
        return w in self.stoi

    def tokenize(self, text: str) -> list[str]:
        tokens: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            m = self._word_re.match(text, i)
            if m:
                w = m.group(0)
                if self._known_word(w):
                    tokens.append(w)
                else:
                    # unknown identifier: emit whole identifier as one token
                    # (Lean-aware: identifiers are atomic)
                    tokens.append(w)
                i = m.end()
                continue
            ch = text[i]
            if ch.isspace():
                # collapse whitespace runs into a single space token
                j = i
                while j < n and text[j].isspace():
                    j += 1
                tokens.append(" ")
                i = j
                continue
            # operators / punctuation
            matched = False
            for op in _OPERATORS:
                if text.startswith(op, i):
                    tokens.append(op)
                    i += len(op)
                    matched = True
                    break
            if not matched:
                tokens.append(ch)
                i += 1
        return tokens

    def encode(self, text: str) -> list[int]:
        return [self.stoi.get(t, 3) for t in self.tokenize(text)]  # 3 = <UNK>

    def decode(self, ids: Iterable[int]) -> str:
        return "".join(self.itos[i] for i in ids)
