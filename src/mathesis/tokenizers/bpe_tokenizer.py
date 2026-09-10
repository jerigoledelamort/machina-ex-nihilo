"""BPE tokenizer wrapper (spec sections 28-30). Option A baseline."""

from __future__ import annotations

from pathlib import Path


class BPETokenizer:
    """HuggingFace tokenizers BPE wrapper trained on the Mathesis corpus."""

    def __init__(self, vocab_size: int = 8000):
        from tokenizers import Tokenizer, models, pre_tokenizers, trainers

        self._vocab_size = vocab_size
        # vocab size is controlled by the trainer, not the model ctor
        self._tk = Tokenizer(models.BPE(unk_token="<UNK>"))
        self._tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        self._trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            special_tokens=["<PAD>", "<BOS>", "<EOS>", "<UNK>"],
        )
        self._trained = False

    def train_from_files(self, files: list[Path]) -> None:
        self._tk.train([str(f) for f in files], self._trainer)
        self._trained = True

    def train_from_iterator(self, texts) -> None:
        self._tk.train_from_iterator(list(texts), self._trainer)
        self._trained = True

    @property
    def vocab_size(self) -> int:
        return self._tk.get_vocab_size()

    def tokenize(self, text: str) -> list[str]:
        return self._tk.encode(text).tokens

    def encode(self, text: str) -> list[int]:
        return self._tk.encode(text).ids

    def decode(self, ids) -> str:
        return self._tk.decode(list(ids), skip_special_tokens=False)

    def save(self, path: Path) -> None:
        self._tk.save(str(path))

    def load(self, path: Path) -> None:
        from tokenizers import Tokenizer

        self._tk = Tokenizer.from_file(str(path))
        self._trained = True
