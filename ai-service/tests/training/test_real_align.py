"""v3 label alignment on synthetic text only."""
from collections import Counter

from training.real_align import align_label, date_candidates, is_programming_language, strip_location

TEXT = """NGUYEN VAN SYNTHETIC
syn@example.test | 0912 345 678
EXPERIENCE
Synthetic Software, Ho Chi Minh City   Jan 2024 - Present
Backend Intern
SKILLS
Languages: Java, Python
English: IELTS 6.5
CERTIFICATES
English B1 2024
"""


def test_helpers():
    assert is_programming_language("Java") and is_programming_language("C# (OOP)")
    assert not is_programming_language("English")
    assert strip_location("Synthetic Software, Ho Chi Minh City") == "Synthetic Software"
    assert strip_location("FPT Software") == "FPT Software"
    assert "Jan 2024" in date_candidates("01/2024") and date_candidates("2024") == []


def test_align_label_v3_conventions():
    label = {"personal_info": {"full_name": "NGUYEN VAN SYNTHETIC", "email": "syn@example.test", "phone": "0912345678"},
             "experience": [{"company": "Synthetic Software, Ho Chi Minh City", "job_title": "Backend Intern",
                             "start_date": "01/2024", "end_date": None, "description": []}],
             "skills": ["Languages: Java"], "certificates": ["English B1 (2024)"],
             "languages": [{"language": "Python", "note": None}, {"language": "English", "note": "IELTS 6.5"}]}
    stats = Counter()
    out = align_label(TEXT, label, stats)
    exp = out["experience"][0]
    assert exp["company"] == "Synthetic Software" and exp["start_date"] == "Jan 2024"
    assert out["personal_info"]["phone"] == "0912345678"
    assert [x["language"] for x in out["languages"]] == ["English"]
    assert "Java" in out["skills"] and "Python" in out["skills"]
    assert out["certificates"] == ["English B1 2024"]
