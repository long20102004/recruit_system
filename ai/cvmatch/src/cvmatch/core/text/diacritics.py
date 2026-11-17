"""Phat hien CV tieng Viet go khong dau (thiet ke 04 A4, nguong `no_diacritics.threshold`).

BERTScore rat nhay voi dau (test T11, F05) nen CV go khong dau duoc gan co `no_diacritics`
va Rerank coi la thieu du lieu phia CV thay vi cham diem thap.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_SYLLABLE_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Tu chuc nang tieng Viet thuong gap, o dang KHONG dau: dung de nhan ra tieng Viet go khong dau.
_VN_NOACC = {
    "va", "cua", "cac", "trong", "nhung", "duoc", "khong", "nguoi", "lam", "viec", "cho", "voi",
    "mot", "nhieu", "phat", "trien", "kinh", "nghiem", "du", "an", "xay", "dung", "he", "thong",
    "quan", "ly", "thiet", "ke", "toi", "uu", "truy", "van", "du", "lieu", "nam", "thang", "cong",
    "ty", "tham", "gia", "nhom", "phan", "mem", "ung", "dung", "khach", "hang", "su", "dung",
    "hieu", "biet", "tot", "nghiep", "dai", "hoc", "chuyen", "nganh", "lap", "trinh", "vien",
    "giam", "thoi", "gian", "bang", "tai", "da", "co", "la", "nay", "theo", "tu", "den",
}
# Tu chuc nang tieng Anh: de khong nham CV tieng Anh la "tieng Viet khong dau".
_EN = {
    "the", "and", "of", "to", "in", "for", "with", "on", "a", "an", "is", "by", "using",
    "developed", "built", "designed", "implemented", "experience", "project", "team", "system",
    "data", "application", "years", "from", "as", "at", "this", "that", "worked", "responsible",
}


def _has_diacritic(word: str) -> bool:
    if "đ" in word or "Đ" in word:
        return True
    return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", word))


def syllables(texts: Iterable[str]) -> list[str]:
    out: list[str] = []
    for t in texts:
        if t:
            out.extend(m.group(0).lower() for m in _SYLLABLE_RE.finditer(t))
    return out


def diacritic_ratio(texts: Iterable[str]) -> float:
    """Ti le am tiet co dau tren tong am tiet (chu cai) cua cac o chu tu do."""
    syl = syllables(texts)
    if not syl:
        return 0.0
    return sum(_has_diacritic(w) for w in syl) / len(syl)


def is_vietnamese(texts: Iterable[str], *, min_syllables: int = 20) -> bool:
    """CV viet tieng Viet (co dau hoac khong dau)?

    Co dau du nhieu -> tieng Viet. Neu gan nhu khong co dau: so tu chuc nang tieng Viet (dang
    khong dau) phai nhieu hon tu chuc nang tieng Anh va chiem >= 15% am tiet.
    """
    syl = syllables(texts)
    if len(syl) < min_syllables:
        return False
    if sum(_has_diacritic(w) for w in syl) / len(syl) >= 0.05:
        return True
    vn = sum(w in _VN_NOACC for w in syl)
    en = sum(w in _EN for w in syl)
    return vn > en and vn / len(syl) >= 0.15


def no_diacritics(texts: Iterable[str], threshold: float = 0.05, *, min_syllables: int = 20) -> bool:
    """Co `no_diacritics`: CV tieng Viet ma ti le am tiet co dau < threshold."""
    texts = list(texts)
    if not is_vietnamese(texts, min_syllables=min_syllables):
        return False
    return diacritic_ratio(texts) < threshold
