"""BM25 trong RAM tren ma tran thua (thiet ke 01 muc 3, 04 A9, 06 view (b)).

Tu cai thay vi dung thu vien de dap ung dung thiet ke A9: chi muc "dung lai theo lo" (vd moi dem),
CV moi nap trong ngay van cham duoc NGAY bang thong ke IDF / do dai trung binh cua lan dung truoc.
Tu chua co trong tu vung cua lan dung bi bo qua cho toi lan dung sau.

Diem: score(d, q) = sum_t idf(t) * tf(t,d)*(k1+1) / (tf(t,d) + k1*(1 - b + b*|d|/avgdl)),
idf(t) = ln(1 + (N - df + 0.5)/(df + 0.5))  (dang Lucene, luon duong). Token lap trong truy van
duoc dem nhieu lan (truy van JD giu nguyen; Luong D tu bo trung khi rut gon CV).
Trong so tung o (d, t) tinh san luc dung -> cham ca kho = mot phep nhan ma tran thua voi vector truy van.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

import numpy as np
import scipy.sparse as sp


class Bm25Index:
    def __init__(self, k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.vocab: dict[str, int] = {}
        self.idf = np.zeros(0, dtype=np.float32)
        self.avgdl = 1.0
        self.n_docs_at_build = 0
        self._base = sp.csr_matrix((0, 0), dtype=np.float32)
        self._extra: list[sp.csr_matrix] = []
        self._cache: sp.csr_matrix | None = None

    # ----------------------------------------------------------------- dung

    def build(self, docs: Sequence[Sequence[str]]) -> "Bm25Index":
        """Dung lai tu dau (theo lo): tu vung, IDF, avgdl co dinh tu day cho toi lan dung sau."""
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d))
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        n = len(docs)
        dfv = np.array([df[t] for t in sorted(df)], dtype=np.float64)
        self.idf = np.log1p((n - dfv + 0.5) / (dfv + 0.5)).astype(np.float32)
        self.avgdl = float(np.mean([len(d) for d in docs])) if n else 1.0
        self.n_docs_at_build = n
        self._base = self._rows(docs)
        self._extra, self._cache = [], None
        return self

    def _rows(self, docs: Iterable[Sequence[str]]) -> sp.csr_matrix:
        indptr, indices, data = [0], [], []
        k1, b, avgdl = self.k1, self.b, max(self.avgdl, 1e-9)
        for d in docs:
            norm = k1 * (1 - b + b * len(d) / avgdl)
            for t, tf in Counter(d).items():
                j = self.vocab.get(t)
                if j is not None:
                    indices.append(j)
                    data.append(tf * (k1 + 1) / (tf + norm))
            indptr.append(len(indices))
        return sp.csr_matrix((np.asarray(data, np.float32), np.asarray(indices, np.int32),
                              np.asarray(indptr, np.int64)), shape=(len(indptr) - 1, len(self.vocab)))

    def append(self, docs: Sequence[Sequence[str]]) -> None:
        """Them tai lieu moi (CV nap trong ngay) voi IDF/avgdl cua lan dung truoc."""
        self._extra.append(self._rows(docs))
        self._cache = None

    @property
    def matrix(self) -> sp.csr_matrix:
        if self._cache is None:
            self._cache = sp.vstack([self._base, *self._extra], format="csr") if self._extra else self._base
        return self._cache

    @property
    def n_docs(self) -> int:
        return self.matrix.shape[0]

    # ----------------------------------------------------------------- cham

    def query_vector(self, query: Sequence[str]) -> np.ndarray:
        q = np.zeros(len(self.vocab), dtype=np.float32)
        for t, c in Counter(query).items():
            j = self.vocab.get(t)
            if j is not None:
                q[j] = c * self.idf[j]
        return q

    def scores(self, query: Sequence[str]) -> np.ndarray:
        """Diem BM25 cua MOI tai lieu (thu tu hang) voi truy van."""
        if not len(self.vocab):
            return np.zeros(self.n_docs, dtype=np.float32)
        return np.asarray(self.matrix @ self.query_vector(query), dtype=np.float32).ravel()
