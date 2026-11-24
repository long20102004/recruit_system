"""A3. An danh hoa (thiet ke 04 A3, 03 muc "Quyen rieng tu").

Bo khoi ban dung de cham: ho ten, email, sdt, dia chi chi tiet, link mang xa hoi, nam sinh, tuoi,
gioi tinh, anh, tinh trang hon nhan, ten truong. Giu: tinh/thanh, nganh, bang cap, nam tot nghiep,
chuc danh, mo ta cong viec, ky nang.
O chu tu do con duoc quet them: email, sdt, URL, va chinh `full_name` (ca dang khong dau).
"""

from __future__ import annotations

import copy
import re
from typing import Any

from cvmatch.core.text.normalize import nfc, strip_diacritics
from cvmatch.ingest.cv.record import CvContext, CvRecord

# Truong ca nhan o cap goc (ten noi bo sau adapter)
PII_TOP_FIELDS = {
    "full_name", "email", "phone", "address", "birth_year", "birth_date", "age", "gender", "sex",
    "photo", "avatar", "image", "marital_status", "nationality", "id_number", "links", "social",
    "socials", "website", "linkedin", "github", "facebook", "references", "referees", "hobbies",
    "interests", "contact",
}
PII_EDU_FIELDS = {"school", "gpa"}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?!\d)")
_URL_RE = re.compile(r"(?:https?://|www\.)\S+|\b(?:linkedin|github|facebook)\.com/\S+", re.I)


def _name_regex(full_name: str | None) -> re.Pattern | None:
    if not full_name or not full_name.strip():
        return None
    name = re.sub(r"\s+", " ", nfc(full_name).strip())
    forms = {name, strip_diacritics(name)}
    parts = name.split(" ")
    if len(parts) >= 2:  # "Nguyễn Văn A" hay duoc viet "A Nguyễn" / "Van A Nguyen"
        forms |= {f"{parts[-1]} {parts[0]}", strip_diacritics(f"{parts[-1]} {parts[0]}")}
    alts = "|".join(re.escape(f).replace(r"\ ", r"\s+") for f in sorted(forms, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alts})(?!\w)", re.I)


def scrub_text(s: str, name_re: re.Pattern | None) -> str:
    s = _EMAIL_RE.sub(" ", s)
    s = _URL_RE.sub(" ", s)
    s = _PHONE_RE.sub(" ", s)
    if name_re is not None:
        s = name_re.sub(" ", s)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def _scrub(obj: Any, name_re: re.Pattern | None) -> Any:
    if isinstance(obj, str):
        return scrub_text(obj, name_re)
    if isinstance(obj, list):
        return [_scrub(x, name_re) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub(v, name_re) for k, v in obj.items()}
    return obj


def anonymize(cv: dict) -> dict:
    name_re = _name_regex(cv.get("full_name"))
    out = {k: copy.deepcopy(v) for k, v in cv.items() if k not in PII_TOP_FIELDS}
    out["education"] = [
        {k: v for k, v in e.items() if k not in PII_EDU_FIELDS} if isinstance(e, dict) else e
        for e in out.get("education") or []
    ]
    return _scrub(out, name_re)


def step_a03(rec: CvRecord, ctx: CvContext) -> CvRecord:
    rec.anon_json = anonymize(rec.raw_json)
    if ctx.patterns.suspected_injection(" ".join(_iter_strings(rec.anon_json))):
        rec.add_flag("suspected_injection")  # 08 muc 6: quet luc nap, chi gan co
    return rec


def _iter_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for x in obj:
            yield from _iter_strings(x)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
