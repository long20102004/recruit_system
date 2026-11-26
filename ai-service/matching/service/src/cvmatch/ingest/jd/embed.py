"""B7 (phan vector). Embedding van ban truy van va tung trach nhiem cua JD, theo LO (thiet ke 05 B7)."""

from __future__ import annotations

import numpy as np

from cvmatch.core.models import Encoder
from cvmatch.ingest.jd.record import JdRecord


def embed_jd_records(records: list[JdRecord], encoder: Encoder) -> None:
    if not records:
        return
    q = encoder.encode([r.query_text or "" for r in records])
    resp_texts = [x.context_text for r in records for x in r.responsibilities]
    rd = encoder.encode(resp_texts).dense if resp_texts else np.zeros((0, encoder.dim), np.float32)
    off = 0
    for i, r in enumerate(records):
        n = len(r.responsibilities)
        r.vectors = {"embed_model": encoder.key(), "dense": q.dense[i].astype(np.float16),
                     "sparse": q.sparse[i], "resp_dense": rd[off:off + n].astype(np.float16)}
        off += n
