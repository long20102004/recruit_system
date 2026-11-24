"""FakeEncoder: cung interface voi BgeM3, vector TAT DINH tu hash van ban - de test khong can GPU/mang.

- Dense: tong vector ngau nhien (seed = hash cua tu) cua cac tu -> hai cau chung tu thi gan nhau.
- Sparse: tan suat tu da chuan hoa.
- Token: moi tu mot token, vector tu hash cua tu (chu thuong) -> tu giong nhau cosine = 1.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from functools import lru_cache

import numpy as np

from cvmatch.core.models.base import EncodeResult, TokenEmb, l2_normalize

_WORD_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


@lru_cache(maxsize=100_000)
def _word_vec(word: str, dim: int) -> np.ndarray:
    seed = int.from_bytes(hashlib.md5(word.encode("utf-8")).digest()[:8], "little")
    v = np.random.default_rng(seed).standard_normal(dim).astype(np.float32)
    v /= np.linalg.norm(v)
    v.setflags(write=False)
    return v


class FakeEncoder:
    def __init__(self, dim: int = 1024, key: str = "fake@0"):
        self.dim = dim
        self._key = key

    def key(self) -> str:
        return self._key

    def encode(self, texts: list[str], batch_size: int | None = None) -> EncodeResult:
        dense = np.zeros((len(texts), self.dim), dtype=np.float32)
        sparse: list[dict[str, float]] = []
        for i, t in enumerate(texts):
            words = [w.lower() for w in _WORD_RE.findall(t or "") if w.strip() and re.match(r"\w", w)]
            for w in words:
                dense[i] += _word_vec(w, self.dim)
            if not words:  # van ban rong: vector co dinh, khong phai 0 (giu chuan L2 = 1)
                dense[i] = _word_vec("<empty>", self.dim)
            cnt = Counter(words)
            total = sum(cnt.values()) or 1
            sparse.append({w: round(c / total, 4) for w, c in cnt.items()})
        return EncodeResult(dense=l2_normalize(dense), sparse=sparse)

    def token_embeddings(self, texts: list[str], layer: int = 24, max_len: int = 2048,
                         batch_size: int | None = None) -> list[TokenEmb]:
        out = []
        for t in texts:
            toks, offs = [], []
            for m in _WORD_RE.finditer(t or ""):
                toks.append(m.group(0))
                offs.append((m.start(), m.end()))
            toks, offs = toks[:max_len], offs[:max_len]
            emb = (np.stack([_word_vec(w.lower(), self.dim) for w in toks])
                   if toks else np.zeros((0, self.dim), dtype=np.float32))
            out.append(TokenEmb(tokens=toks, offsets=offs, emb=emb))
        return out
