"""Ham chuan hoa dung chung cho CV (A4), JD (B2) va alias KB.

Thiet ke 04 A4: thu tu (1) NFC, (2) chu thuong, (3) bo ky tu trang tri + gop khoang trang,
(4) KHONG xoa `#`, `+`, `.`, `/` trong ten cong nghe. Ham o day khong xoa dau cau nao,
nen token duoc bao ve (`c#`, `c++`, `.net`, `node.js`, `ci/cd`) giu nguyen.

- `to_raw`   = buoc 1 + 3: nguon cua `text_raw` (giu dau, giu hoa/thuong) cho BERTScore.
- `normalize` = buoc 1-3: dung cho khop tu (A5, A9) va luu `anon_json`, `text`.
CV, JD va alias KB PHAI dung cung ham nay; khac ham la khop lech.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

# Ky tu trang tri hay gap trong CV/JD (bullet, sao, mui ten, o vuong...). Khong gom '-', '*', '+'
# vi co the la mot phan noi dung (c++, "-" trong khoang ngay); viec bo dau gach dau dong o
# dau dong do A7 lo.
_DECOR = "•●○◦▪▫■□◆◇❖★☆✓✔✗✘➢➤►▶▸▹‣∙⁃➔→⇒※"
_DECOR_RE = re.compile(f"[{re.escape(_DECOR)}]")
# Ky tu vo hinh / khoang trang dac biet
_INVISIBLE_RE = re.compile("[​‌‍⁠﻿­]")
_SPACE_RE = re.compile(r"[ \t  -   　]+")


def _clean_lines(s: str, keep_newlines: bool) -> str:
    s = _INVISIBLE_RE.sub("", s)
    s = _DECOR_RE.sub(" ", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_SPACE_RE.sub(" ", ln).strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln]
    return ("\n" if keep_newlines else " ").join(lines)


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def to_raw(s: str | None, *, keep_newlines: bool = True) -> str:
    """Buoc 1 + 3 cua A4: NFC, bo ky tu trang tri, gop khoang trang. Giu dau, giu hoa/thuong.

    `keep_newlines=True` giu xuong dong (gop dong trong) de A7 con tach duoc doan van thanh gach.
    """
    if not s:
        return ""
    return _clean_lines(nfc(s), keep_newlines)


def normalize(s: str | None, *, keep_newlines: bool = False) -> str:
    """Buoc 1-3 cua A4: NFC, chu thuong, bo trang tri, gop khoang trang. Khong pha token bao ve."""
    if not s:
        return ""
    # lower() co the sinh dang to hop (vd 'İ') -> NFC lai lan nua
    return nfc(_clean_lines(nfc(s), keep_newlines).lower())


def strip_diacritics(s: str) -> str:
    """Bo dau tieng Viet: 'lập_trình_viên' -> 'lap_trinh_vien', 'đ' -> 'd'."""
    s = s.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFC", "".join(c for c in decomposed if not unicodedata.combining(c)))


# --------------------------------------------------------------------------- dia diem


class LocationNormalizer:
    """Alias dia diem -> ma tinh/thanh (`config/patterns/locations.yaml`).

    Khop ca dang co dau va khong dau; uu tien khop nguyen chuoi, roi alias dai nhat nam trong chuoi.
    """

    def __init__(self, mapping: dict[str, list[str]]):
        alias_to_code: dict[str, str] = {}
        for code, aliases in mapping.items():
            for a in [code.replace("_", " "), *aliases]:
                na = normalize(a)
                for form in {na, strip_diacritics(na)}:
                    alias_to_code.setdefault(form, code)
        self._exact = alias_to_code
        ordered = sorted(alias_to_code, key=len, reverse=True)
        self._re = re.compile(r"(?<!\w)(" + "|".join(re.escape(a) for a in ordered) + r")(?!\w)")

    @classmethod
    def from_file(cls, path: str | Path) -> "LocationNormalizer":
        with Path(path).open(encoding="utf-8") as f:
            return cls(yaml.safe_load(f))

    def __call__(self, s: str | None) -> str | None:
        if not s:
            return None
        n = normalize(s)
        for form in (n, strip_diacritics(n)):
            if form in self._exact:
                return self._exact[form]
        for form in (n, strip_diacritics(n)):
            m = self._re.search(form)
            if m:
                return self._exact[m.group(1)]
        return None


@lru_cache(maxsize=4)
def _default_location_normalizer(path: str) -> LocationNormalizer:
    return LocationNormalizer.from_file(path)


def normalize_location(s: str | None, path: str | Path | None = None) -> str | None:
    """Tien ich: dung file locations.yaml cua config dang chay."""
    if path is None:
        from cvmatch.core.config import get_config

        path = get_config().pattern_path("locations")
    return _default_location_normalizer(str(path))(s)


# --------------------------------------------------------------------------- ngay thang

_MONTHS_EN = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_PRESENT = {"hiện tại", "hien tai", "nay", "đến nay", "den nay", "present", "now", "current",
            "today", "hiện nay", "hien nay", "ongoing"}

_Y = r"(?P<y>(?:19|20)\d{2})"
_M = r"(?P<m>0?[1-9]|1[0-2])"
_YM_PATTERNS = [
    re.compile(rf"^{_Y}\s*[-/.]\s*{_M}$"),                               # 2022-03, 2022/3
    re.compile(rf"^{_M}\s*[-/.]\s*{_Y}$"),                               # 03/2022, 3-2022
    re.compile(rf"^(?:tháng|thang|th|t)\.?\s*{_M}\s*(?:[-/.,]|năm|nam)?\s*{_Y}$"),  # tháng 3/2022, T3/2022
    re.compile(rf"^\d{{1,2}}\s*[-/.]\s*{_M}\s*[-/.]\s*{_Y}$"),           # 15/03/2022
    re.compile(rf"^{_Y}\s*[-/.]\s*{_M}\s*[-/.]\s*\d{{1,2}}$"),           # 2022-03-15
]
_EN_MONTH_RE = re.compile(r"^(?P<mon>[a-z]{3,9})\.?\s*,?\s*" + _Y + "$")
_YEAR_ONLY_RE = re.compile("^" + _Y + "$")


def is_present(s: str | None) -> bool:
    """'hiện tại', 'present'... -> True (viec dang lam)."""
    return bool(s) and normalize(s).strip(" .") in _PRESENT


def parse_ym(s: str | int | None, *, role: str = "start") -> str | None:
    """Dua ngay thang ve `YYYY-MM`. Khong doc duoc -> None (caller gan co `date_unparsed`).

    Chi co nam: `role='start'` -> `YYYY-01`, `role='end'` -> `YYYY-12` (quy uoc, de khong
    thoi phong so thang; ghi `dates_quality = partial` o A6).
    Gia tri "hiện tại"/"present" tra None; dung `is_present` de nhan biet.
    """
    if s is None:
        return None
    if isinstance(s, int):
        s = str(s)
    t = normalize(s).strip(" .,")
    if not t:
        return None
    for pat in _YM_PATTERNS:
        m = pat.match(t)
        if m:
            return f"{int(m.group('y')):04d}-{int(m.group('m')):02d}"
    m = _EN_MONTH_RE.match(t)
    if m:
        mon = _MONTHS_EN.get(m.group("mon")[:4]) or _MONTHS_EN.get(m.group("mon")[:3])
        if mon:
            return f"{int(m.group('y')):04d}-{mon:02d}"
    m = _YEAR_ONLY_RE.match(t)
    if m:
        return f"{int(m.group('y')):04d}-{'01' if role == 'start' else '12'}"
    return None


def is_year_only(s: str | int | None) -> bool:
    return s is not None and bool(_YEAR_ONLY_RE.match(normalize(str(s)).strip(" .,")))
