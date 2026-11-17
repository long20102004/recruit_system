"""Interface encoder dung chung cho Tang 0 (A10, B7), Retrieve va BERTScore (T10)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class EncodeResult:
    dense: np.ndarray                 # (n, dim) float32, da chuan hoa L2
    sparse: list[dict[str, float]]    # tu -> trong so (lexical weights cua bge-m3)


@dataclass
class TokenEmb:
    """Embedding tung token cua MOT cau (BERTScore). Da bo <s>, </s>; moi hang chuan L2 = 1."""

    tokens: list[str]
    offsets: list[tuple[int, int]]    # vi tri ky tu trong van ban dau vao (gop sub-word -> tu o T10)
    emb: np.ndarray                   # (n_tok, dim) float32


class Encoder(Protocol):
    dim: int

    def key(self) -> str:
        """Gia tri `embed_model` ghi vao moi ban ghi, vd 'bge-m3@5617a9f61b'."""
        ...

    def encode(self, texts: list[str], batch_size: int | None = None) -> EncodeResult: ...

    def token_embeddings(self, texts: list[str], layer: int = 24, max_len: int = 2048,
                         batch_size: int | None = None) -> list[TokenEmb]: ...


def l2_normalize(x: np.ndarray, axis: int = -1) -> np.ndarray:
    n = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / np.maximum(n, 1e-12)
