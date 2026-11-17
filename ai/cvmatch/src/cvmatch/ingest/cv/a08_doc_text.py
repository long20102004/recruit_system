"""A8. Ghep van ban tai lieu theo MAU CO DINH (thiet ke 04 A8). Mau co phien ban
(`prep.doc_template_version`, nam trong pipeline_version): doi mau -> chay lai A8-A10 toan kho.

    Chức danh: senior java developer
    Tóm tắt: backend developer 4 năm kinh nghiệm java
    Kinh nghiệm: senior java developer. xây dựng api .... tối ưu .... Công nghệ: java, spring boot, kafka
    Dự án: (không có)
    Kỹ năng: java, spring boot, postgresql, docker
    Học vấn: kỹ thuật phần mềm

- Chi dung `anon_json` da chuan hoa; khong ten cong ty, ten truong, so thich, nguoi tham chieu.
- Kinh nghiem / du an xep moi -> cu; nhieu muc noi bang " | ".
- Gach trong doc_text la cac gach DUOC GIU o A7 (cung bo loc).
"""

from __future__ import annotations

from cvmatch.ingest.cv.record import CvContext, CvRecord

EMPTY = "(không có)"
LABELS = ("Chức danh", "Tóm tắt", "Kinh nghiệm", "Dự án", "Kỹ năng", "Học vấn")


def _item_text(head: str | None, bullets: list[str], techs: list[str]) -> str:
    parts = [p for p in [head, *bullets] if p]
    s = ". ".join(parts)
    if techs:
        s = f"{s}. Công nghệ: {', '.join(techs)}" if s else f"Công nghệ: {', '.join(techs)}"
    return s


def build_doc_parts(rec: CvRecord) -> dict[str, str]:
    """Noi dung tung dong (khong nhan). Dung lai o A9 de token BM25 khong dinh nhan."""
    cv = rec.anon_json or {}
    by_item: dict[tuple[str, int], list[str]] = {}
    for b in rec.bullets:
        by_item.setdefault((b.section, b.item_idx), []).append(b.text)

    def section_text(section: str, key: str, head_field: str) -> str:
        items = cv.get(key) or []
        texts = []
        for idx, src in enumerate(rec.item_order.get(section, [])):
            it = items[src]
            techs = [t for t in (it.get("technologies") or []) if isinstance(t, str) and t]
            t = _item_text(it.get(head_field), by_item.get((section, idx), []), techs)
            if t:
                texts.append(t)
        return " | ".join(texts)

    exp_items = cv.get("experiences") or []
    order = rec.item_order.get("experience", [])
    title = exp_items[order[0]].get("title") if order else None
    skills = [s for s in (cv.get("skills") or []) if isinstance(s, str) and s]
    majors = [e.get("major") for e in (cv.get("education") or []) if e.get("major")]
    return {
        "Chức danh": title or "",
        "Tóm tắt": cv.get("summary") or "",
        "Kinh nghiệm": section_text("experience", "experiences", "title"),
        "Dự án": section_text("project", "projects", "name"),
        "Kỹ năng": ", ".join(skills),
        "Học vấn": ", ".join(majors),
    }


def step_a08(rec: CvRecord, ctx: CvContext) -> CvRecord:
    parts = build_doc_parts(rec)
    rec.doc_text = "\n".join(f"{lab}: {(parts[lab] or EMPTY).replace(chr(10), ' ')}" for lab in LABELS)
    return rec
