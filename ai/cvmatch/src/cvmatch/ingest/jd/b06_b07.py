"""B6 tach trach nhiem (+ co chung chung), B7 token BM25 truy van + embedding."""

from __future__ import annotations

import numpy as np

from cvmatch.core.models import Encoder
from cvmatch.core.text.bm25_tokens import skill_tokens, tokens_acc, tokens_noacc
from cvmatch.core.text.normalize import normalize, to_raw
from cvmatch.ingest.cv.a07_bullets import n_words
from cvmatch.ingest.jd.b01_b03 import QUERY_LABELS, query_parts
from cvmatch.ingest.jd.record import JdRecord, PrepContext, Responsibility


def step_b06(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    title = (rec.norm_json or {}).get("title") or ""
    out = []
    for line in rec.raw_json.get("responsibilities") or []:
        text_raw = to_raw(line, keep_newlines=False)
        if n_words(text_raw) < ctx.cfg.prep.bullet.min_words:
            continue
        text = normalize(text_raw)
        out.append(Responsibility(idx=len(out), text=text, text_raw=text_raw,
                                  context_text=f"{title}: {text}" if title else text,
                                  is_generic=ctx.patterns.is_generic_resp(text)))
    rec.responsibilities = out
    return rec


def step_b07_tokens(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    """Token truy van BM25 = token KHONG DAU cua noi dung van ban truy van (khong nhan dong) + skill
    token. JD luu san token truy van, khong vao chi muc (thiet ke B7)."""
    parts = query_parts(rec.norm_json or {})
    text = "\n".join(parts[lab] for lab in QUERY_LABELS if parts[lab])
    rec.bm25_query_tokens = (tokens_noacc(tokens_acc(text, ctx.segmenter))
                             + skill_tokens(s.skill_id for s in rec.skills_found))
    return rec


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
