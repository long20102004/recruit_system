"""EX2, EX3: loi giai thich bang mau xac dinh (thiet ke 08 muc 3).

`build_context(item)` -> du lieu cho mau (chi so, chuoi lay tu facts, ma co); toan bo cau chu nam trong
file mau Jinja2 (`explain.template_file`). `render(ctx, mask=True)` thay MOI gia tri do code dien bang
"§" (tru ma co / loai) de EX4 kiem phan chu cua mau ma khong bi du lieu CV/JD lam nhieu.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import jinja2

from cvmatch.core.contracts import FinalItem

MASK = "§"
_UNMASKED_KEYS = {"kind", "level", "reason", "flags", "notes"}
_NOTE_FLAGS = ("low_data_quality", "no_diacritics", "has_negation_bullets", "location_mismatch", "check_language")
_REL_LABEL = {"parent": "cha", "child": "con", "sibling": "anh em"}


@dataclass
class Rendered:
    text: str
    masked: str
    context: dict


@lru_cache(maxsize=8)
def _template(path: str) -> jinja2.Template:
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=False,
                             undefined=jinja2.StrictUndefined, autoescape=False)
    return env.from_string(Path(path).read_text(encoding="utf-8"))


def fmt_years(y: float) -> str:
    """4.7 -> '4,7'; 5.0 -> '5'."""
    s = f"{y:.1f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def question_phrase(resp_text: str) -> str:
    """'Thiet ke API ...' -> 'thiet ke API ...' (giu nguyen tu viet tat nhu 'API ...')."""
    t = resp_text.strip().rstrip(".;:")
    if len(t) > 1 and t[0].isupper() and not t[1].isupper():
        t = t[0].lower() + t[1:]
    return t


def word_spans(text: str, words: list[str]) -> list[tuple[int, int]]:
    """Vi tri (theo thu tu) cua tung tu trong `text` - de frontend to dam."""
    spans, pos = [], 0
    for w in words:
        m = re.compile(re.escape(w), re.IGNORECASE).search(text, pos)
        if m is None:
            m = re.compile(re.escape(w), re.IGNORECASE).search(text)
        if m is not None:
            spans.append((m.start(), m.end()))
            pos = m.end() if m.start() >= pos else pos
    return spans


def build_context(item: FinalItem, names: dict[str, str], band: str, band_label: str, *,
                  max_examples: int = 3, max_questions: int = 3) -> dict:
    name = lambda sid: names.get(sid, sid)  # noqa: E731
    sf = item.skill_facts
    n_req = len(sf.met) + len(sf.partial) + len(sf.missing)
    skills = {"n_req": n_req, "n_met": len(sf.met), "met": [name(m.skill) for m in sf.met],
              "partial": [{"found": name(p.found), "required": name(p.required), "relation": _REL_LABEL[p.relation]}
                          for p in sf.partial],
              "missing": [name(s) for s in sf.missing]}

    b4_missing = item.missing.get("B4")
    reason = "ok" if item.resp_facts else ("cv_side" if b4_missing == "cv_side" else "none")
    met = [f for f in item.resp_facts if f.level == "met" and f.evidence_id in item.evidence]
    examples = []
    for f in met[:max_examples]:
        ev = item.evidence[f.evidence_id]
        examples.append({"resp_id": f.resp_id, "resp_text": f.resp_text, "evidence_id": f.evidence_id,
                         "evidence_text": ev.text_raw, "matched": list(f.matched_words),
                         "missing": list(f.missing_words), "flags": list(ev.flags),
                         "highlight": word_spans(f.resp_text, f.matched_words)})
    gaps = [{"resp_id": f.resp_id, "resp_text": f.resp_text, "level": f.level,
             "missing_words": list(f.missing_words) if f.level == "partial" else [],
             "evidence_id": f.evidence_id if f.level == "partial" else None}
            for f in item.resp_facts if f.level != "met"]
    resp = {"reason": reason, "n_met": len([f for f in item.resp_facts if f.level == "met"]),
            "n_total": len(item.resp_facts), "examples": examples, "gaps": gaps}

    ef = item.experience_facts
    experience = {"years": fmt_years(ef.relevant_years) if ef.relevant_years is not None else None,
                  "role_group": ef.role_group_cv}

    notes = [f for f in _NOTE_FLAGS if f in item.flags]
    if b4_missing == "cv_side" and "no_diacritics" not in item.flags:
        notes.append("no_bullets")
    if item.missing.get("B2") == "cv_side":
        notes.append("years_missing")
    if item.missing.get("B1") == "cv_side":
        notes.append("role_missing")

    questions = [{"kind": "resp", "text": question_phrase(g["resp_text"])} for g in gaps if g["level"] == "partial"]
    questions += [{"kind": "resp", "text": question_phrase(g["resp_text"])} for g in gaps if g["level"] != "partial"]
    questions += [{"kind": "skill", "text": s} for s in skills["missing"]]

    a1 = item.features.A1
    return {"score": item.score, "scale": 100, "band": band, "band_label": band_label, "cap_applied": item.cap_applied,
            "a1_pct": round(100 * a1) if a1 is not None else None, "skills": skills, "resp": resp,
            "experience": experience, "notes": notes, "questions": questions[:max_questions]}


def _mask(x, key: str | None = None):
    if key in _UNMASKED_KEYS:
        return x
    if isinstance(x, dict):
        return {k: _mask(v, k) for k, v in x.items()}
    if isinstance(x, list):
        return [_mask(v, key) for v in x]
    if isinstance(x, bool) or x is None:
        return x
    return MASK


def render(ctx: dict, template_path: str | Path) -> Rendered:
    tpl = _template(str(template_path))
    text = tpl.render(**ctx).strip() + "\n"
    masked = tpl.render(**_mask(ctx)).strip() + "\n"
    return Rendered(text=re.sub(r"\n{3,}", "\n\n", text), masked=re.sub(r"\n{3,}", "\n\n", masked), context=ctx)
