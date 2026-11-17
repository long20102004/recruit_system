"""A7. Tach gach dau dong (thiet ke 04 A7).

- `description` la mang -> moi phan tu mot gach (phan tu co xuong dong thi tach tiep).
- La doan van -> tach theo xuong dong, ky tu gach dau dong, roi dau cham cau.
- Bo gach < `bullet.min_words` tu va gach chi chua ngay thang.
- `text_raw` = to_raw (giu dau, hoa/thuong); `text` = normalize; `context_text` = "chuc danh: gach"
  (du an: "ten du an: gach").
- Co `has_negation`, `is_coursework` theo danh sach mau.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cvmatch.core.text.normalize import normalize, to_raw
from cvmatch.ingest.cv.record import Bullet, CvContext, CvRecord

_MARKER = r"[-*+•●○◦▪▫■□◆◇❖★☆✓✔➢➤►▶▸‣∙⁃–—]"
_LEAD_MARKER_RE = re.compile(rf"^\s*(?:{_MARKER}+|\(?\d{{1,2}}[.)](?=\s))\s*")
_INLINE_SPLIT_RE = re.compile(r"\s*[•●▪◦‣∙■□★➢➤►▶✓✔]\s*|\s+[-–—]\s+(?=[^\W\d_])|\s*;\s+")
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"\w+")
_DATE_WORDS = {"tháng", "thang", "năm", "nam", "to", "đến", "den", "from", "hiện", "tại", "hien",
               "tai", "nay", "present", "now", "t"}


@dataclass(frozen=True)
class BulletPart:
    path: str            # vi tri trong JSON, vd "description[1]" hoac "description"
    raw: str             # NFC + to_raw, da bo ky tu gach dau dong o dau
    kept: bool           # qua bo loc do dai / ngay thang
    pos: int | None      # thu tu trong cac gach DUOC GIU cua muc (None neu bi bo)


def _strip_marker(s: str) -> str:
    return _LEAD_MARKER_RE.sub("", s, count=1).strip()


def _split_sentences(s: str) -> list[str]:
    """Tach cau nhung khong cat "v.v." / so thap phan: chi cat khi cau sau bat dau bang chu hoa."""
    pieces = _SENT_SPLIT_RE.split(s)
    out: list[str] = []
    for p in pieces:
        if out and p and not p[0].isupper():
            out[-1] = f"{out[-1]} {p}"
        else:
            out.append(p)
    return out


def _split_text(s: str, *, sentences: bool) -> list[str]:
    parts: list[str] = []
    for line in s.replace("\r", "\n").split("\n"):
        line = _strip_marker(line)
        if not line:
            continue
        for chunk in _INLINE_SPLIT_RE.split(line):
            chunk = _strip_marker(chunk)
            if not chunk:
                continue
            parts.extend(_split_sentences(chunk) if sentences else [chunk])
    return [p.strip() for p in parts if p.strip()]


def is_date_only(s: str) -> bool:
    words = [w for w in _WORD_RE.findall(s.lower()) if not w.isdigit() and w not in _DATE_WORDS]
    return not words


def n_words(s: str) -> int:
    return len(_WORD_RE.findall(s))


def split_description(desc, min_words: int) -> list[BulletPart]:
    """Mo ta cua MOT muc -> cac phan, theo thu tu; danh dau phan duoc giu va `pos` cua no."""
    raw_parts: list[tuple[str, str]] = []
    if isinstance(desc, list):
        for k, el in enumerate(desc):
            if isinstance(el, str):
                raw_parts.extend((f"description[{k}]", p) for p in _split_text(el, sentences=False))
    elif isinstance(desc, str):
        raw_parts.extend(("description", p) for p in _split_text(desc, sentences=True))

    out: list[BulletPart] = []
    pos = 0
    for path, p in raw_parts:
        raw = to_raw(p, keep_newlines=False)
        kept = bool(raw) and n_words(raw) >= min_words and not is_date_only(raw)
        out.append(BulletPart(path, raw, kept, pos if kept else None))
        if kept:
            pos += 1
    return out


def item_context(section: str, item_norm: dict) -> str | None:
    """Ngu canh gan truoc gach khi tao vector: chuc danh (kinh nghiem) / ten du an (du an)."""
    if section == "experience":
        return item_norm.get("title") or None
    return item_norm.get("name") or item_norm.get("role") or None


SECTIONS = (("experience", "experiences"), ("project", "projects"))


def step_a07(rec: CvRecord, ctx: CvContext) -> CvRecord:
    min_words = ctx.cfg.prep.bullet.min_words
    bullets: list[Bullet] = []
    for section, key in SECTIONS:
        raw_items = (rec.anon_raw or {}).get(key) or []
        norm_items = (rec.anon_json or {}).get(key) or []
        for item_idx, src in enumerate(rec.item_order.get(section, [])):
            ctx_label = item_context(section, norm_items[src])
            for part in split_description(raw_items[src].get("description"), min_words):
                if not part.kept:
                    continue
                text = normalize(part.raw)
                bullets.append(Bullet(
                    section=section,
                    item_idx=item_idx,
                    pos=part.pos,
                    text=text,
                    text_raw=part.raw,
                    context_text=f"{ctx_label}: {text}" if ctx_label else text,
                    has_negation=ctx.patterns.has_negation(text),
                    is_coursework=ctx.patterns.is_coursework(text),
                ))
    rec.bullets = bullets
    rec.meta.n_bullets = len(bullets)
    return rec
