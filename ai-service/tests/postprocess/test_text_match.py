"""Unit tests for text normalization, matching and span extraction."""

import pytest

from app.postprocess.text_match import (
    contains,
    digits,
    find_span,
    normalize,
    normalize_with_map,
)


def test_normalize_basic():
    """Verify normalize handles whitespace collapse, casing, and Vietnamese diacritics."""
    assert normalize("  Công ty  ĐẠI Việt ") == "cong ty dai viet"
    assert normalize("Đại Học Quốc Gia") == "dai hoc quoc gia"
    assert normalize("Kỹ Sư Phần Mềm") == "ky su phan mem"
    assert normalize("sinh viên") == "sinh vien"


def test_normalize_empty_and_whitespace():
    """Verify normalize handles empty, None, and whitespace-only strings."""
    assert normalize("") == ""
    assert normalize(None) == ""
    assert normalize("    ") == ""
    assert normalize("\t\n\r") == ""


def test_normalize_with_map():
    """Verify char_map maps normalized characters back to exact source indices."""
    text = "  Công ty  ĐẠI Việt "
    norm_str, char_map = normalize_with_map(text)

    assert norm_str == "cong ty dai viet"
    assert len(norm_str) == len(char_map)

    # Check key character mappings in the original text:
    # text[2] == 'C' -> norm_str[0] == 'c'
    assert char_map[0] == 2
    assert text[char_map[0]] == "C"

    # text[3] == 'ô' (decomposed, mark dropped) -> norm_str[1] == 'o'
    assert char_map[1] == 3
    assert text[char_map[1]] == "ô"

    # text[6] == ' ' -> norm_str[4] == ' '
    assert char_map[4] == 6
    assert text[char_map[4]] == " "

    # text[11] == 'Đ' -> norm_str[8] == 'd'
    assert char_map[8] == 11
    assert text[char_map[8]] == "Đ"

    # text[12] == 'Ạ' -> norm_str[9] == 'a'
    assert char_map[9] == 12
    assert text[char_map[9]] == "Ạ"

    # text[13] == 'I' -> norm_str[10] == 'i'
    assert char_map[10] == 13
    assert text[char_map[10]] == "I"

    # text[17] == 'ệ' -> norm_str[14] == 'e'
    assert char_map[14] == 17
    assert text[char_map[14]] == "ệ"

    # text[18] == 't' -> norm_str[15] == 't'
    assert char_map[15] == 18
    assert text[char_map[15]] == "t"

    # Slicing from first mapped index to last mapped index (+1) captures the full inner phrase
    span = text[char_map[0] : char_map[-1] + 1]
    assert span == "Công ty  ĐẠI Việt"


def test_normalize_with_map_empty():
    """Verify normalize_with_map returns empty string and empty list for blank inputs."""
    assert normalize_with_map("") == ("", [])
    assert normalize_with_map(None) == ("", [])
    assert normalize_with_map("   ") == ("", [])


def test_contains():
    """Verify contains is accent- and case-insensitive on both raw and normalized CV text."""
    cv_raw = "Kinh nghiệm làm việc tại Công ty Cổ phần Công nghệ ABC"
    cv_norm = normalize(cv_raw)

    # Raw CV text
    assert contains(cv_raw, "cong ty co phan")
    assert contains(cv_raw, "CÔNG TY CỔ PHẦN")
    assert contains(cv_raw, "Công ty")
    assert contains(cv_raw, "cong ty")
    assert not contains(cv_raw, "FPT Software")

    # Pre-normalized CV text
    assert contains(cv_norm, "Công ty Cổ phần")
    assert contains(cv_norm, "cong ty co phan")
    assert contains(cv_norm, "CONG TY")
    assert not contains(cv_norm, "FPT Software")

    # Empty inputs
    assert not contains("", "Cong ty")
    assert not contains(cv_raw, "")
    assert not contains(None, "Cong ty")
    assert not contains(cv_raw, None)


def test_find_span_exact_returns_original_diacritics():
    """find_span exact match must return verbatim original text from CV with accents."""
    cv_text = "Học vấn: Đại học Bách Khoa Hà Nội, chuyên ngành Công nghệ Thông tin."

    # Matching without accents or with different case returns the exact CV substring
    res = find_span("Dai hoc Bach Khoa Ha Noi", cv_text)
    assert res == "Đại học Bách Khoa Hà Nội"

    res_upper = find_span("ĐẠI HỌC BÁCH KHOA HÀ NỘI", cv_text)
    assert res_upper == "Đại học Bách Khoa Hà Nội"


def test_find_span_fpt_software():
    """find_span 'Cong ty FPT Softwar' on CV containing 'Công ty FPT Software' returns span containing 'Cong ty FPT Softwar' with accents from CV."""
    cv_text = "Thực tập sinh tại Công ty FPT Software từ tháng 06/2023 đến nay."

    res = find_span("Cong ty FPT Softwar", cv_text)
    assert res == "Công ty FPT Software"

    # Near-miss fuzzy match snaps to the full company name in CV
    res_fuzzy = find_span("Cong ty FPT Softwaer", cv_text, threshold=85.0)
    assert res_fuzzy == "Công ty FPT Software"


def test_find_span_short_value():
    """Short value < 3 characters requires exact containment; returns None if not in CV."""
    cv_text = "Tôi tốt nghiệp ĐH Bách Khoa, có chứng chỉ AWS."

    # < 3 chars absent from CV -> None (no fuzzy matching)
    assert find_span("AI", cv_text) is None
    assert find_span("XY", cv_text) is None

    # < 3 chars present in CV -> exact match found
    assert find_span("ĐH", cv_text) == "ĐH"
    assert find_span("dh", cv_text) == "ĐH"


def test_find_span_fabricated():
    """Fabricated entity not in CV returns None."""
    cv_text = "Kinh nghiệm: Lập trình viên Backend tại Công ty Cổ phần VNG từ 2021 đến 2023."
    assert find_span("Google DeepMind", cv_text) is None
    assert find_span("Shopee Singapore", cv_text) is None


def test_find_span_empty_and_threshold():
    """find_span returns None for empty inputs or when match score is below threshold."""
    cv_text = "Làm việc tại Viettel Telecom."

    assert find_span("", cv_text) is None
    assert find_span("Viettel", "") is None
    assert find_span(None, cv_text) is None
    assert find_span("Viettel", None) is None

    # Below high threshold
    assert find_span("VinAI Research", cv_text, threshold=95.0) is None


def test_digits():
    """digits extracts digit characters and ignores spaces, dashes, parentheses and country prefixes."""
    assert digits("+84 912-345-678") == "84912345678"
    assert digits("0912.345.678") == "0912345678"
    assert digits("(+84) 024-3754-7865") == "8402437547865"
    assert digits("no digits in this string") == ""
    assert digits("") == ""
    assert digits(None) == ""
