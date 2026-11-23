"""A9. Token BM25 (thiet ke 04 A9): token bao ve -> tach tu -> ban khong dau -> skill token.

Tach tren noi dung cac dong cua van ban tai lieu (A8) nhung KHONG gom nhan dong ("Chức danh:"...)
va gia tri rong "(không có)", de cac tu nay khong vao chi muc. Ba truong luu rieng.
"""

from __future__ import annotations

from cvmatch.core.text.bm25_tokens import bm25_fields
from cvmatch.ingest.cv.a08_doc_text import LABELS, build_doc_parts
from cvmatch.ingest.cv.record import Bm25Doc, CvContext, CvRecord


def step_a09(rec: CvRecord, ctx: CvContext) -> CvRecord:
    parts = build_doc_parts(rec)
    text = "\n".join(parts[lab] for lab in LABELS if parts[lab])
    f = bm25_fields(text, [s.skill_id for s in rec.skills_found], ctx.segmenter)
    rec.bm25 = Bm25Doc(**f)
    return rec
