"""Regressions found on the first real CV (2026-11-04); synthetic values only."""

from app.postprocess import postprocess

CV = """NGUYEN VAN SYNTHETIC
syn@example.test | 0900000099
EXPERIENCE
Công ty cổ phần công nghệ Synthetic Việt Nam      October 2025 - May 2026
• Developed RESTful APIs for CMS using Spring Boot
TECHNICAL SKILL
● Backend: Spring Boot(Spring REST, Spring data)
● Programming Languages: Java, C++,
"""


def _exp(title):
    return {"company": "Công ty cổ phần công nghệ Synthetic Việt Nam", "job_title": title,
            "start_date": "October 2025", "end_date": "May 2026",
            "description": ["Developed RESTful APIs for CMS using Spring Boot"]}


def test_experience_without_title_is_kept():
    out, stats = postprocess({"experience": [_exp(None)]}, CV)
    assert len(out["experience"]) == 1 and out["experience"][0]["job_title"] is None
    assert stats.experience_removed_type == 0


def test_invented_title_is_nulled_not_removed():
    out, stats = postprocess({"experience": [_exp("Backend Developer")]}, CV)
    assert len(out["experience"]) == 1 and out["experience"][0]["job_title"] is None
    assert stats.titles_nulled == 1


def test_student_title_still_removes_experience():
    cv = CV.replace("Synthetic Việt Nam ", "Synthetic Việt Nam Sinh viên ")
    out, _ = postprocess({"experience": [_exp("Sinh viên")]}, cv)
    assert out["experience"] == []


def test_ungrounded_skill_removed_grounded_kept():
    out, stats = postprocess({"skills": ["Spring Boot (Spring REST, Spring Data)", "Java", "C++", "Python"]}, CV)
    assert out["skills"] == ["Spring Boot (Spring REST, Spring Data)", "Java", "C++"]
    assert stats.items_removed_ungrounded == 1


def test_list_valued_scalar_is_joined_not_repr():
    from app.postprocess.schema import normalize_profile

    out = normalize_profile({"personal_projects": [{"name": "BOOKSTORE", "role": ["Developer"]},
                                                   {"name": "X", "role": ["Backend", "Tester"]},
                                                   {"name": "Y", "role": []}]})
    assert [p["role"] for p in out["personal_projects"]] == ["Developer", "Backend, Tester", None]
