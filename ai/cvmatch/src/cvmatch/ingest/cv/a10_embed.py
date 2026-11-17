"""A10. Tao embedding (thiet ke 04 A10), theo LO nhieu CV mot lan.

- Vector tai lieu: dense + sparse cua `doc_text` (A8 - da viet thuong nhung CON DAU, dung y
  "van ban tai lieu co dau"; khong dung ban khong dau cua A9).
- Vector gach: dense cua tung `context_text` (A7, da gan "chuc danh: ...").
- Luu float16; ghi `embed_model` kem moi vector.
"""

from __future__ import annotations

import numpy as np

from cvmatch.core.models import Encoder
from cvmatch.ingest.cv.record import CvRecord


def embed_records(records: list[CvRecord], encoder: Encoder, batch_size: int | None = None) -> None:
    if not records:
        return
    docs = encoder.encode([r.doc_text or "" for r in records], batch_size)
    bullet_texts = [b.context_text for r in records for b in r.bullets]
    bdense = (encoder.encode(bullet_texts, batch_size).dense if bullet_texts
              else np.zeros((0, encoder.dim), dtype=np.float32))
    off = 0
    for i, r in enumerate(records):
        n = len(r.bullets)
        r.vectors = {
            "embed_model": encoder.key(),
            "doc_dense": docs.dense[i].astype(np.float16),
            "doc_sparse": docs.sparse[i],
            "bullet_dense": bdense[off:off + n].astype(np.float16),
        }
        off += n
