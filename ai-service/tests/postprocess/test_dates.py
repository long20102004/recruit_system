"""Feature 011: start/end swapped when a timeline prints the end date first (synthetic data)."""

from app.postprocess.dates import fix_date_order, parse_month


def test_parse_formats():
    assert parse_month("03/2025") == parse_month("Mar 2025") == parse_month("March 2025") == parse_month("T3/2025")
    assert parse_month("Tháng 3/2025") == parse_month("3-2025")
    assert parse_month("Present") is None and parse_month(None) is None


def test_swap_only_when_reversed():
    p = {"experience": [{"start_date": "03/2025", "end_date": "06/2024"},
                        {"start_date": "06/2024", "end_date": "03/2025"},
                        {"start_date": "2023", "end_date": None}],
         "personal_projects": [{"start_date": "Dec 2022", "end_date": "Sep 2022"}]}
    out = fix_date_order(p)
    assert out["experience"][0] == {"start_date": "06/2024", "end_date": "03/2025"}
    assert out["experience"][1] == {"start_date": "06/2024", "end_date": "03/2025"}
    assert out["experience"][2]["start_date"] == "2023"
    assert out["personal_projects"][0] == {"start_date": "Sep 2022", "end_date": "Dec 2022"}
