"""B6. Tach trach nhiem cua JD thanh tung cau (+ co chung chung) (thiet ke 05 B6)."""

from __future__ import annotations

from cvmatch.core.text.normalize import normalize, to_raw
from cvmatch.ingest.cv.bullets import _split_text, n_words
from cvmatch.ingest.jd.record import JdRecord, PrepContext, Responsibility


def _lines(rec: JdRecord, ctx: PrepContext) -> list[str]:
    """Dong trach nhiem cua JD. V-05 (prep.jd.split_min_words): dong dai (JD nhap mot doan van tren form) -> tach cau
    bang cung ham tach gach cua A7, de B4 co tung cau de so voi gach CV."""
    lines = [x for x in (rec.raw_json.get("responsibilities") or []) if isinstance(x, str)]
    limit = ctx.cfg.prep.jd.split_min_words
    if limit is None:
        return lines
    out: list[str] = []
    for line in lines:
        out.extend(_split_text(line, sentences=True) if n_words(line) > limit else [line])
    return out


def step_b06(rec: JdRecord, ctx: PrepContext) -> JdRecord:
    title = (rec.norm_json or {}).get("title") or ""
    out = []
    for line in _lines(rec, ctx):
        text_raw = to_raw(line, keep_newlines=False)
        if n_words(text_raw) < ctx.cfg.prep.bullet.min_words:
            continue
        text = normalize(text_raw)
        out.append(Responsibility(idx=len(out), text=text, text_raw=text_raw,
                                  context_text=f"{title}: {text}" if title else text,
                                  is_generic=ctx.patterns.is_generic_resp(text)))
    rec.responsibilities = out
    return rec
