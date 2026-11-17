"""Can khop token -> bang chung (thiet ke 07 muc 5.3 "Can khop token").

Voi cap (trach nhiem j, gach khop nhat): moi TU cua cau JD (gop sub-word theo vi tri ky tu, bo tu
dung) co sim = max cosine cua cac token con voi moi token cua gach. sim >= `align.word_sim_min` ->
`matched_words`, con lai -> `missing_words`. Tu tra ve theo chuoi GOC (`text_raw`).
"""

from __future__ import annotations

import re

import numpy as np

from cvmatch.core.models.base import TokenEmb
from cvmatch.rerank.bertscore.prepare import Prepared

_WORD_RE = re.compile(r"[\w][\w+#./-]*[\w+#]|[\w]", re.UNICODE)
STOPWORDS = {
    "và", "cho", "các", "của", "với", "những", "một", "là", "trong", "bằng", "để", "được", "có", "theo",
    "từ", "đến", "về", "tại", "hoặc", "hay", "khi", "này", "đó", "the", "and", "for", "with", "of", "to",
    "in", "on", "a", "an", "or", "by", "as", "at", "from", "n",
}


def word_spans(text: str, segmenter=None) -> list[tuple[int, int]]:
    """Vi tri tung TU. Co `segmenter` (pyvi) -> gop am tiet thanh tu ("thiet_ke" -> "thiet ke");
    khong co -> moi am tiet / chuoi khong khoang trang la mot tu."""
    if segmenter is None:
        return [(m.start(), m.end()) for m in _WORD_RE.finditer(text)]
    spans, pos = [], 0
    for tok in segmenter.segment(text):
        parts = [p for p in tok.split("_") if p]
        if not parts or not _WORD_RE.search(tok):
            continue
        start = text.find(parts[0], pos)
        if start < 0:
            continue
        end, ok = start + len(parts[0]), True
        for p in parts[1:]:
            k = text.find(p, end)
            if k < 0 or text[end:k].strip():
                ok = False
                break
            end = k + len(p)
        if not ok:
            end = start + len(parts[0])
        spans.append((start, end))
        pos = end
    return spans


def _literal(word: str, cv_text_low: str) -> bool:
    return re.search(r"(?<![\w+#])" + re.escape(word.lower()) + r"(?![\w+#])", cv_text_low) is not None


def align_words(jd_prep: Prepared, jd_emb: TokenEmb, cv_emb: TokenEmb, word_sim_min: float = 0.75,
                segmenter=None, cv_text: str | None = None) -> tuple[list[str], list[str], list[tuple[str, float]]]:
    """-> (matched_words, missing_words, [(tu, sim)]) theo thu tu trong cau JD.

    `cv_text` (van ban DA CHUAN BI cua gach): neu co, tu xuat hien nguyen van trong gach cung tinh la khop.
    """
    cv_low = cv_text.lower() if cv_text else None
    if not len(jd_emb.tokens):
        return [], [], []
    if len(cv_emb.tokens):
        tok_sim = (jd_emb.emb @ cv_emb.emb.T).max(axis=1)
    else:
        tok_sim = np.zeros(len(jd_emb.tokens), dtype=np.float32)
    matched, missing, detail = [], [], []
    for w0, w1 in word_spans(jd_prep.text, segmenter):
        idx = [k for k, (a, b) in enumerate(jd_emb.offsets) if a < w1 and b > w0 and b > a]
        if not idx:
            continue
        r0, r1 = jd_prep.to_raw_span(w0, w1)
        word = jd_prep.raw[r0:r1]
        if word.lower() in STOPWORDS or jd_prep.text[w0:w1].lower() in STOPWORDS:
            continue
        sim = float(tok_sim[idx].max())
        detail.append((word, round(sim, 4)))
        hit = sim >= word_sim_min or (cv_low is not None and _literal(jd_prep.text[w0:w1], cv_low))
        (matched if hit else missing).append(word)
    return matched, missing, detail
