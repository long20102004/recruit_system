"""Profile variants for dataset v5 (feature 014): fictional fixtures only."""

import random
from copy import deepcopy

from training.synth.render import validate_profile
from training.synth.variants import _timeline, many_jobs, student


def _profile(i: int, jobs: int = 1, projects: int = 1) -> dict:
    return {
        "id": f"fic-{i:03d}", "level": "middle", "lang": "en", "role": "Developer",
        "profile": {
            "personal_info": {"full_name": f"Fiction {i}", "email": f"f{i}@example.com", "phone": None, "github_url": None},
            "objective": "Fictional objective.",
            "education": [{"school": "Fiction University", "major": "CS", "start_year": 2015, "end_year": 2019, "gpa": None}],
            "experience": [{"company": f"Company {i}-{k}", "job_title": "Dev", "start_date": "01/2020", "end_date": None,
                            "description": ["First bullet.", "Second bullet.", "Third bullet."]} for k in range(jobs)],
            "personal_projects": [{"name": f"Project {i}-{k}", "role": None, "team_size": None, "start_date": None,
                                   "end_date": None, "github_url": None, "description": ["Did a thing.", "More."],
                                   "tech_stack": ["Java", "Go"]} for k in range(projects)],
            "skills": ["Java"], "certificates": [], "honours": ["Best Employee 2022"], "languages": [],
        },
        "extras": {"headline": None, "address": None, "dob": None, "linkedin": None,
                   "skill_groups": [{"group": "Languages", "items": ["Java"]}], "interests": []},
    }


def _month_index(value: str) -> int:
    m, y = value.split("/")
    return int(y) * 12 + int(m)


def test_timeline_newest_first_non_overlapping():
    rng = random.Random(0)
    for _ in range(50):
        pairs = _timeline(6, rng, current=True)
        assert pairs[0][1] is None
        for (start, end), (prev_start, _) in zip(pairs[1:], pairs):
            assert _month_index(start) < _month_index(end) <= _month_index(prev_start)


def test_many_jobs_shape_and_validity():
    pool = [_profile(i, jobs=2, projects=3) for i in range(10)]
    base = deepcopy(pool[0])
    rec = many_jobs(pool[0], pool, random.Random(1))
    assert pool[0] == base  # input untouched
    p = rec["profile"]
    assert rec["id"] == "fic-000.m"
    assert 4 <= len(p["experience"]) <= 6
    assert len({j["company"] for j in p["experience"]}) == len(p["experience"])
    assert all(1 <= len(j["description"]) <= 2 for j in p["experience"])
    assert 5 <= len(p["personal_projects"]) <= 9
    assert all(len(x["description"]) == 1 for x in p["personal_projects"])
    assert validate_profile(rec) == []


def test_student_has_no_jobs():
    pool = [_profile(i, jobs=2, projects=1) for i in range(10)]
    rec = student(pool[0], pool, random.Random(2))
    p = rec["profile"]
    assert rec["id"] == "fic-000.s" and rec["level"] == "junior"
    assert p["experience"] == []
    assert 2 <= len(p["personal_projects"]) <= 5
    assert p["honours"] == []
    assert validate_profile(rec) == []
