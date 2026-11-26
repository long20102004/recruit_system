"""B7 (phan token). Token truy van BM25 cua JD (thiet ke 05 B7)."""

from __future__ import annotations

from cvmatch.core.text.bm25_tokens import skill_tokens, tokens_acc, tokens_noacc
from cvmatch.ingest.jd.prepare import QUERY_LABELS, query_parts
from cvmatch.ingest.jd.record import JdRecord, PrepContext


def step_b07_tokens(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    """Token truy van BM25 = token KHONG DAU cua noi dung van ban truy van (khong nhan dong) + skill
    token. JD luu san token truy van, khong vao chi muc (thiet ke B7)."""
    parts = query_parts(rec.norm_json or {})
    text = "\n".join(parts[lab] for lab in QUERY_LABELS if parts[lab])
    rec.bm25_query_tokens = (tokens_noacc(tokens_acc(text, ctx.segmenter))
                             + skill_tokens(s.skill_id for s in rec.skills_found))
    return rec
