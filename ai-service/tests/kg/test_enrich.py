"""Unit tests for KG enrichment of extracted CV profiles."""

from __future__ import annotations

import copy
import json

from app.kb.linker import Link, SkillLinker
from app.kg import enrich as kg_module_enrich
from app.kg.enrich import enrich
from app.postprocess.pipeline import PostprocessStats


# ---------------------------------------------------------------------------
# Test Helpers: Synthetic In-Memory Fakes
# ---------------------------------------------------------------------------


class FakeLinker:
    """Simple duck-typed skill linker mapping raw skill strings to Link objects."""

    def __init__(
        self,
        mapping: dict[str, Link] | None = None,
        surfaces: dict[str, int] | None = None,
    ) -> None:
        self.mapping = mapping or {}
        self.surfaces = surfaces or {}

    def link_many(self, raws: list[str]) -> list[Link]:
        results: list[Link] = []
        seen_ids: set[int] = set()
        for raw in raws:
            link = self.mapping.get(
                raw,
                Link(
                    raw=raw,
                    skill_id=None,
                    name=None,
                    category=None,
                    method="unlinked",
                    score=0.0,
                ),
            )
            if link.skill_id is None:
                results.append(link)
            elif link.skill_id not in seen_ids:
                seen_ids.add(link.skill_id)
                results.append(link)
        return results


class FakeKB:
    """Duck-typed KnowledgeBase carrying linker, skills, edges, and school resolver."""

    def __init__(
        self,
        linker: FakeLinker | SkillLinker | None = None,
        skills: dict[int, tuple[str, str]] | None = None,
        edges: dict[int, list[tuple[str, int]]] | None = None,
        schools: dict[str, tuple[int, str]] | None = None,
        related: dict[int, list[tuple[int, float]]] | None = None,
    ) -> None:
        self.linker = linker or FakeLinker()
        self.skills = skills or {}
        self.edges = edges or {}
        self.schools = schools or {}
        self.related = related or {}

    def link_school(self, raw: str | None) -> tuple[int, str] | None:
        if not raw:
            return None
        return self.schools.get(str(raw).strip())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_package_export() -> None:
    """app.kg must export enrich."""
    assert kg_module_enrich is enrich


def test_implied_skills_transitive_and_via() -> None:
    """Spring Data JPA PART_OF Spring Boot REQUIRES Java -> implied Spring Boot (depth 1) and Java (depth 2)."""
    skills = {
        1: ("Spring Data JPA", "Backend"),
        2: ("Spring Boot", "Backend"),
        3: ("Java", "Programming Language"),
    }
    edges = {
        1: [("PART_OF", 2)],
        2: [("REQUIRES", 3)],
    }
    linker = FakeLinker({
        "Spring Data JPA": Link(
            raw="Spring Data JPA",
            skill_id=1,
            name="Spring Data JPA",
            category="Backend",
            method="exact",
            score=100.0,
        )
    })
    kb = FakeKB(linker=linker, skills=skills, edges=edges)

    profile = {
        "personal_info": {"email": "dev@example.com", "phone": "0123456789"},
        "skills": ["Spring Data JPA"],
    }

    result = enrich(profile, kb)

    # skills_normalized check
    assert result["skills_normalized"] == [
        {
            "raw": "Spring Data JPA",
            "id": 1,
            "name": "Spring Data JPA",
            "category": "Backend",
            "method": "exact",
        }
    ]

    # implied_skills check (depth 1: Spring Boot via Spring Data JPA, depth 2: Java via Spring Boot)
    assert len(result["implied_skills"]) == 2
    assert result["implied_skills"][0] == {
        "id": 2,
        "name": "Spring Boot",
        "category": "Backend",
        "via": [{"from": "Spring Data JPA", "rel": "PART_OF"}],
    }
    assert result["implied_skills"][1] == {
        "id": 3,
        "name": "Java",
        "category": "Programming Language",
        "via": [{"from": "Spring Boot", "rel": "REQUIRES"}],
    }


def test_implied_skill_already_present_excluded() -> None:
    """Implied skill already present in skills_normalized is not repeated in implied_skills."""
    skills = {
        1: ("Spring Data JPA", "Backend"),
        2: ("Spring Boot", "Backend"),
        3: ("Java", "Programming Language"),
    }
    edges = {
        1: [("PART_OF", 2)],
        2: [("REQUIRES", 3)],
    }
    linker = FakeLinker({
        "Spring Data JPA": Link(
            raw="Spring Data JPA",
            skill_id=1,
            name="Spring Data JPA",
            category="Backend",
            method="exact",
            score=100.0,
        ),
        "Java": Link(
            raw="Java",
            skill_id=3,
            name="Java",
            category="Programming Language",
            method="exact",
            score=100.0,
        ),
    })
    kb = FakeKB(linker=linker, skills=skills, edges=edges)

    profile = {
        "personal_info": {"email": "dev@example.com", "phone": "0123456789"},
        "skills": ["Spring Data JPA", "Java"],
    }

    result = enrich(profile, kb)

    # Both are in skills_normalized
    assert {s["id"] for s in result["skills_normalized"]} == {1, 3}

    # Only Spring Boot is implied; Java is excluded because candidate already has it
    assert len(result["implied_skills"]) == 1
    assert result["implied_skills"][0]["id"] == 2
    assert result["implied_skills"][0]["name"] == "Spring Boot"


def test_cycle_safe_no_infinite_loop() -> None:
    """Graph cycle A -> B -> A terminates cleanly without infinite loop."""
    skills = {
        10: ("SkillA", "CategoryA"),
        20: ("SkillB", "CategoryB"),
    }
    edges = {
        10: [("REQUIRES", 20)],
        20: [("REQUIRES", 10)],
    }
    linker = FakeLinker({
        "SkillA": Link(
            raw="SkillA",
            skill_id=10,
            name="SkillA",
            category="CategoryA",
            method="exact",
            score=100.0,
        )
    })
    kb = FakeKB(linker=linker, skills=skills, edges=edges)

    profile = {
        "personal_info": {"email": "test@ptit.edu.vn", "phone": "0987654321"},
        "skills": ["SkillA"],
    }

    result = enrich(profile, kb)

    # Implies SkillB once; SkillA is already visited, so loop terminates
    assert len(result["implied_skills"]) == 1
    assert result["implied_skills"][0]["id"] == 20
    assert result["implied_skills"][0]["via"] == [{"from": "SkillA", "rel": "REQUIRES"}]


def test_skills_unlinked_count_in_flags() -> None:
    """Unlinked skills produce SKILLS_UNLINKED flag with exact count."""
    skills = {1: ("React", "Frontend")}
    edges = {}
    linker = FakeLinker({
        "React": Link(
            raw="React",
            skill_id=1,
            name="React",
            category="Frontend",
            method="exact",
            score=100.0,
        )
    })
    kb = FakeKB(linker=linker, skills=skills, edges=edges)

    profile = {
        "personal_info": {"email": "test@ptit.edu.vn", "phone": "0987654321"},
        "skills": ["React", "Some Unknown Skill A", "Some Unknown Skill B"],
    }

    result = enrich(profile, kb)

    unlinked_flags = [f for f in result["flags"] if f["code"] == "SKILLS_UNLINKED"]
    assert len(unlinked_flags) == 1
    assert unlinked_flags[0] == {
        "code": "SKILLS_UNLINKED",
        "count": 2,
        "field": "skills",
    }


def test_school_normalized_and_unknown_school_no_flag() -> None:
    """School PTIT is normalized, unknown school becomes None, and no flag is raised."""
    kb = FakeKB(
        schools={
            "PTIT": (187, "Học viện Công nghệ Bưu chính Viễn thông"),
            "Posts and Telecommunications Institute of Technology": (
                187,
                "Học viện Công nghệ Bưu chính Viễn thông",
            ),
        }
    )

    profile = {
        "personal_info": {"email": "student@ptit.edu.vn", "phone": "0988776655"},
        "education": [
            {"school": "PTIT", "major": "Software Engineering"},
            {"school": "NonExistent University XYZ", "major": "Business"},
            {"school": None, "major": "Unknown"},
        ],
    }

    result = enrich(profile, kb)

    edu = result["education"]
    assert edu[0]["school_normalized"] == {
        "id": 187,
        "name": "Học viện Công nghệ Bưu chính Viễn thông",
    }
    assert edu[1]["school_normalized"] is None
    assert edu[2]["school_normalized"] is None

    # Never raise flags for unlinked schools
    flag_codes = [f["code"] for f in result["flags"]]
    assert "MISSING_SCHOOL" not in flag_codes
    assert not any("school" in str(f.get("field", "")) for f in result["flags"])


def test_flags_from_postprocess_stats_and_dict() -> None:
    """Flags correctly aggregate counts from PostprocessStats instance and plain dict."""
    kb = FakeKB()

    # 1. From PostprocessStats
    pp_stats = PostprocessStats(
        items_removed_ungrounded=2,
        education_removed=1,
        projects_removed=3,
        contacts_nulled=2,
        experience_removed_ungrounded=1,
        experience_removed_type=2,
    )
    profile = {
        "personal_info": {"email": "dev@ptit.edu.vn", "phone": "0123456789"},
        "skills": [],
    }

    result_stats = enrich(profile, kb, pp_stats=pp_stats)
    flags_stats = result_stats["flags"]

    assert {
        "code": "UNGROUNDED_REMOVED",
        "count": 6,  # 2 + 1 + 3
        "field": None,
    } in flags_stats

    assert {
        "code": "CONTACT_NULLED",
        "count": 2,
        "field": None,
    } in flags_stats

    assert {
        "code": "EXPERIENCE_REMOVED",
        "count": 3,  # 1 + 2
        "field": None,
    } in flags_stats

    # 2. From plain dict
    dict_stats = {
        "items_removed_ungrounded": 1,
        "education_removed": 0,
        "projects_removed": 1,
        "contacts_nulled": 1,
        "experience_removed_ungrounded": 0,
        "experience_removed_type": 1,
    }
    result_dict = enrich(profile, kb, pp_stats=dict_stats)
    flags_dict = result_dict["flags"]

    assert {
        "code": "UNGROUNDED_REMOVED",
        "count": 2,
        "field": None,
    } in flags_dict

    assert {
        "code": "CONTACT_NULLED",
        "count": 1,
        "field": None,
    } in flags_dict

    assert {
        "code": "EXPERIENCE_REMOVED",
        "count": 1,
        "field": None,
    } in flags_dict


def test_missing_contact_flag() -> None:
    """MISSING_CONTACT raised only when email and phone are both missing or empty."""
    kb = FakeKB()

    # Both empty/None -> flag raised
    prof_no_contacts = {
        "personal_info": {"email": None, "phone": "   "},
        "skills": [],
    }
    res1 = enrich(prof_no_contacts, kb)
    assert {
        "code": "MISSING_CONTACT",
        "count": None,
        "field": "personal_info",
    } in res1["flags"]

    # No personal_info at all -> flag raised
    prof_missing_section = {"skills": []}
    res2 = enrich(prof_missing_section, kb)
    assert {
        "code": "MISSING_CONTACT",
        "count": None,
        "field": "personal_info",
    } in res2["flags"]

    # Email present, phone empty -> flag NOT raised
    prof_email_only = {
        "personal_info": {"email": "hello@world.com", "phone": None},
        "skills": [],
    }
    res3 = enrich(prof_email_only, kb)
    assert not any(f["code"] == "MISSING_CONTACT" for f in res3["flags"])

    # Email None, phone present -> flag NOT raised
    prof_phone_only = {
        "personal_info": {"email": None, "phone": "0987654321"},
        "skills": [],
    }
    res4 = enrich(prof_phone_only, kb)
    assert not any(f["code"] == "MISSING_CONTACT" for f in res4["flags"])


def test_skills_goc_khong_doi() -> None:
    """Original skills field is unchanged by linking or implication."""
    skills = {1: ("Java", "Backend"), 2: ("Spring Boot", "Backend")}
    edges = {2: [("REQUIRES", 1)]}
    linker = FakeLinker({
        "Spring Boot": Link(
            raw="Spring Boot",
            skill_id=2,
            name="Spring Boot",
            category="Backend",
            method="exact",
            score=100.0,
        )
    })
    kb = FakeKB(linker=linker, skills=skills, edges=edges)

    original_skills = ["Spring Boot", "Unlinked Custom Skill"]
    profile = {
        "personal_info": {"email": "test@ptit.edu.vn", "phone": "0987654321"},
        "skills": list(original_skills),
    }

    result = enrich(profile, kb)

    # original skills field in returned dict must match input exactly
    assert result["skills"] == original_skills
    # Java is in implied_skills, but never injected into result["skills"]
    assert "Java" not in result["skills"]


def test_input_not_mutated() -> None:
    """enrich function must never mutate its input dictionary."""
    skills = {1: ("Python", "Programming Language")}
    linker = FakeLinker({
        "Python": Link(
            raw="Python",
            skill_id=1,
            name="Python",
            category="Programming Language",
            method="exact",
            score=100.0,
        )
    })
    kb = FakeKB(linker=linker, skills=skills)

    input_profile = {
        "personal_info": {"full_name": "Test User", "email": "a@b.com", "phone": "123"},
        "skills": ["Python"],
        "education": [{"school": "PTIT", "major": "IT"}],
    }
    input_snapshot = copy.deepcopy(input_profile)

    enrich(input_profile, kb)

    assert input_profile == input_snapshot


def test_flags_never_contain_cv_values() -> None:
    """Flags payload must never leak candidate raw skills, emails, or personal details."""
    secret_email = "super_confidential_candidate@ptit.edu.vn"
    secret_phone = "0987654321098"
    secret_skill = "SecretProprietaryLanguage"

    kb = FakeKB()
    stats = PostprocessStats(
        items_removed_ungrounded=1,
        contacts_nulled=1,
        experience_removed_ungrounded=1,
    )
    profile = {
        "personal_info": {"email": secret_email, "phone": secret_phone},
        "skills": [secret_skill],
    }

    result = enrich(profile, kb, pp_stats=stats)
    serialized_flags = json.dumps(result["flags"])

    assert secret_email not in serialized_flags
    assert secret_phone not in serialized_flags
    assert secret_skill not in serialized_flags


def test_real_skill_linker_integration() -> None:
    """Enrich works with real SkillLinker instance and synthetic dictionary."""
    skills = {
        101: ("React", "Frontend"),
        102: ("JavaScript", "Programming Language"),
    }
    aliases = {
        "react": 101,
        "reactjs": 101,
        "javascript": 102,
        "js": 102,
    }
    surfaces = {
        "React": 101,
        "ReactJS": 101,
        "JavaScript": 102,
    }
    linker = SkillLinker(skills=skills, aliases=aliases, surfaces=surfaces)
    edges = {101: [("REQUIRES", 102)]}
    kb = FakeKB(linker=linker, skills=skills, edges=edges)

    profile = {
        "personal_info": {"email": "fe@dev.com", "phone": "123"},
        "skills": ["ReactJS", "UnknownLibrary123"],
    }

    result = enrich(profile, kb)

    assert len(result["skills_normalized"]) == 2
    assert result["skills_normalized"][0]["id"] == 101
    assert result["skills_normalized"][0]["name"] == "React"
    assert result["skills_normalized"][1]["id"] is None
    assert result["skills_normalized"][1]["method"] == "unlinked"

    assert len(result["implied_skills"]) == 1
    assert result["implied_skills"][0]["name"] == "JavaScript"
    assert result["implied_skills"][0]["via"] == [{"from": "React", "rel": "REQUIRES"}]


def test_implied_skills_sorting_by_depth_then_name() -> None:
    """Implied skills are deterministically sorted by depth, then casefolded name."""
    skills = {
        1: ("RootSkill", "Backend"),
        2: ("Zookeeper", "Infrastructure"),
        3: ("ActiveMQ", "Messaging"),
        4: ("Kafka", "Messaging"),
    }
    # RootSkill requires Zookeeper and ActiveMQ at depth 1; ActiveMQ requires Kafka at depth 2
    edges = {
        1: [("REQUIRES", 2), ("REQUIRES", 3)],
        3: [("REQUIRES", 4)],
    }
    linker = FakeLinker({
        "RootSkill": Link(
            raw="RootSkill",
            skill_id=1,
            name="RootSkill",
            category="Backend",
            method="exact",
            score=100.0,
        )
    })
    kb = FakeKB(linker=linker, skills=skills, edges=edges)

    profile = {
        "personal_info": {"email": "dev@test.com", "phone": "111"},
        "skills": ["RootSkill"],
    }

    result = enrich(profile, kb)
    implied = result["implied_skills"]

    # Depth 1 items: ActiveMQ then Zookeeper (alphabetical)
    # Depth 2 items: Kafka
    assert [item["name"] for item in implied] == ["ActiveMQ", "Zookeeper", "Kafka"]


def test_fixed_flags_order() -> None:
    """Flags appear in fixed order: UNGROUNDED_REMOVED, CONTACT_NULLED, EXPERIENCE_REMOVED, SKILLS_UNLINKED, MISSING_CONTACT."""
    kb = FakeKB()
    stats = {
        "items_removed_ungrounded": 1,
        "contacts_nulled": 1,
        "experience_removed_ungrounded": 1,
    }
    profile = {
        "personal_info": {"email": None, "phone": None},
        "skills": ["UnlinkedSkillA"],
    }

    result = enrich(profile, kb, pp_stats=stats)
    codes = [f["code"] for f in result["flags"]]

    assert codes == [
        "UNGROUNDED_REMOVED",
        "CONTACT_NULLED",
        "EXPERIENCE_REMOVED",
        "SKILLS_UNLINKED",
        "MISSING_CONTACT",
    ]


def test_empty_profile_does_not_crash() -> None:
    """Empty or None fields in profile do not crash enrich."""
    kb = FakeKB()
    result = enrich({}, kb)

    assert result["skills_normalized"] == []
    assert result["implied_skills"] == []
    assert result["skills_detected"] == []
    assert result["related_skills"] == []
    assert result["flags"] == [
        {"code": "MISSING_CONTACT", "count": None, "field": "personal_info"}
    ]


# ---------------------------------------------------------------------------
# US2: skills_detected tests
# ---------------------------------------------------------------------------


def test_skills_detected_sources_and_ordering() -> None:
    """skills_detected populates source model/text/both with CV-first then model-only order."""
    skills = {
        1: ("Python", "Programming Language"),
        2: ("Java", "Programming Language"),
        3: ("Docker", "DevOps"),
        4: ("Kubernetes", "DevOps"),
        5: ("AWS", "Cloud"),
    }
    linker = FakeLinker({
        "Java": Link(raw="Java", skill_id=2, name="Java", category="Programming Language", method="exact", score=100.0),
        "Kubernetes": Link(raw="Kubernetes", skill_id=4, name="Kubernetes", category="DevOps", method="exact", score=100.0),
        "AWS": Link(raw="AWS", skill_id=5, name="AWS", category="Cloud", method="exact", score=100.0),
        "CustomFramework": Link(raw="CustomFramework", skill_id=None, name=None, category=None, method="unlinked", score=0.0),
    })
    kb = FakeKB(linker=linker, skills=skills)

    profile = {
        "personal_info": {"email": "engineer@test.com", "phone": "0987654321"},
        "skills": ["Java", "Kubernetes", "CustomFramework", "AWS"],
    }
    # In cv_text, Docker appears first (pos 14), Java second (pos 27), Python third (pos 46)
    cv_text = "Proficient in Docker, then Java, and finally Python."

    result = enrich(profile, kb, cv_text=cv_text)

    # 1. Docker: found in text only -> "text"
    # 2. Java: found in text and extracted by model -> "both"
    # 3. Python: found in text only -> "text"
    # 4. Kubernetes: model only -> "model"
    # 5. AWS: model only -> "model"
    # Unlinked CustomFramework (id is None) is excluded.
    assert result["skills_detected"] == [
        {"id": 3, "name": "Docker", "category": "DevOps", "source": "text"},
        {"id": 2, "name": "Java", "category": "Programming Language", "source": "both"},
        {"id": 1, "name": "Python", "category": "Programming Language", "source": "text"},
        {"id": 4, "name": "Kubernetes", "category": "DevOps", "source": "model"},
        {"id": 5, "name": "AWS", "category": "Cloud", "source": "model"},
    ]


def test_skills_detected_no_duplicate_ids() -> None:
    """skills_detected dedupes repeated mentions in text and model."""
    skills = {
        1: ("Python", "Programming Language"),
        2: ("Docker", "DevOps"),
    }
    linker = FakeLinker({
        "Python": Link(raw="Python", skill_id=1, name="Python", category="Programming Language", method="exact", score=100.0),
        "Python 3": Link(raw="Python 3", skill_id=1, name="Python", category="Programming Language", method="exact", score=100.0),
    })
    kb = FakeKB(linker=linker, skills=skills)

    profile = {
        "personal_info": {"email": "dev@test.com", "phone": "123"},
        "skills": ["Python", "Python 3"],
    }
    cv_text = "Python expert. Love writing Python scripts with Docker."

    result = enrich(profile, kb, cv_text=cv_text)

    # Python appears multiple times in text and model, but must appear only once (both).
    # Docker appears once in text (text).
    assert result["skills_detected"] == [
        {"id": 1, "name": "Python", "category": "Programming Language", "source": "both"},
        {"id": 2, "name": "Docker", "category": "DevOps", "source": "text"},
    ]


def test_skills_detected_cv_text_none_or_empty() -> None:
    """When cv_text is None or whitespace, only model skills are returned with source 'model'."""
    skills = {
        1: ("Python", "Programming Language"),
        2: ("Go", "Programming Language"),
    }
    linker = FakeLinker({
        "Python": Link(raw="Python", skill_id=1, name="Python", category="Programming Language", method="exact", score=100.0),
        "UnlinkedTool": Link(raw="UnlinkedTool", skill_id=None, name=None, category=None, method="unlinked", score=0.0),
    })
    kb = FakeKB(linker=linker, skills=skills)
    profile = {
        "personal_info": {"email": "dev@test.com", "phone": "123"},
        "skills": ["Python", "UnlinkedTool"],
    }

    expected = [{"id": 1, "name": "Python", "category": "Programming Language", "source": "model"}]

    # cv_text is None
    res_none = enrich(profile, kb, cv_text=None)
    assert res_none["skills_detected"] == expected

    # cv_text is empty string
    res_empty = enrich(profile, kb, cv_text="")
    assert res_empty["skills_detected"] == expected

    # cv_text is whitespace only
    res_spaces = enrich(profile, kb, cv_text="   \n\t  ")
    assert res_spaces["skills_detected"] == expected

    # Legacy caller (without cv_text argument)
    res_legacy = enrich(profile, kb)
    assert res_legacy["skills_detected"] == expected


def test_skills_detected_short_skills_no_false_positive() -> None:
    """Short skills like 'Go' and 'C' (len <= 3) do not match lowercase english words."""
    skills = {
        1: ("Go", "Programming Language"),
        2: ("C", "Programming Language"),
    }
    kb = FakeKB(skills=skills)

    # Lowercase 'go' and 'c' in general sentences must NOT match
    cv_text_false = "I like to go shopping, take a bus, and see a movie."
    result_false = enrich({}, kb, cv_text=cv_text_false)
    assert result_false["skills_detected"] == []

    # Exact uppercase 'Go' and 'C' must match
    cv_text_true = "Skilled in Go and C programming languages."
    result_true = enrich({}, kb, cv_text=cv_text_true)
    assert result_true["skills_detected"] == [
        {"id": 1, "name": "Go", "category": "Programming Language", "source": "text"},
        {"id": 2, "name": "C", "category": "Programming Language", "source": "text"},
    ]


def test_skills_detected_long_surface_alias_matched() -> None:
    """Long aliases in linker.surfaces (> 3 chars) match case-insensitively, short aliases are skipped."""
    skills = {
        1: ("Go", "Programming Language"),
    }
    # "golang" has len 6 > 3 (included), "g" has len 1 <= 3 (skipped)
    linker = FakeLinker(surfaces={"golang": 1, "g": 1})
    kb = FakeKB(linker=linker, skills=skills)

    # Long alias 'golang' matches case-insensitively
    cv_text = "Experienced in golang development."
    result = enrich({}, kb, cv_text=cv_text)
    assert result["skills_detected"] == [
        {"id": 1, "name": "Go", "category": "Programming Language", "source": "text"}
    ]

    # Short alias 'g' does not trigger false positives
    cv_text_short = "A big dog runs in the garden."
    result_short = enrich({}, kb, cv_text=cv_text_short)
    assert result_short["skills_detected"] == []


def test_skills_detected_finder_cached() -> None:
    """Finder is constructed once and cached per KB instance."""
    skills = {
        1: ("Python", "Programming Language"),
    }
    kb = FakeKB(skills=skills)
    assert getattr(kb, "_skill_finder", None) is None

    # First call constructs finder and stores in cache / kb attribute
    res1 = enrich({}, kb, cv_text="Python developer")
    finder1 = getattr(kb, "_skill_finder", None)
    assert finder1 is not None

    # Second call reuses the cached finder
    res2 = enrich({}, kb, cv_text="Python developer")
    finder2 = getattr(kb, "_skill_finder", None)
    assert finder2 is finder1
    assert res1["skills_detected"] == res2["skills_detected"]


def test_skills_detected_kb_missing_skills_degrades_gracefully() -> None:
    """Missing or empty skills in KB gracefully skips text scan without raising."""
    profile = {
        "personal_info": {"email": "dev@test.com", "phone": "123"},
        "skills": ["CustomSkill"],
    }
    # KB with empty skills
    kb_empty = FakeKB(skills={})
    res_empty = enrich(profile, kb_empty, cv_text="Some cv text")
    assert res_empty["skills_detected"] == []

    # KB is None
    res_none = enrich(profile, None, cv_text="Some cv text")
    assert res_none["skills_detected"] == []


# ---------------------------------------------------------------------------
# US2: related_skills tests
# ---------------------------------------------------------------------------


def test_related_skills_from_kb() -> None:
    """related_skills retrieves co-occurring skills from kb.related with correct via and sorting."""
    skills = {
        1: ("Python", "Programming Language"),
        2: ("Git", "Tool"),
        3: ("GitHub", "Tool"),
        4: ("GitLab", "Tool"),
    }
    linker = FakeLinker({
        "Git": Link(raw="Git", skill_id=2, name="Git", category="Tool", method="exact", score=100.0),
    })
    related = {
        2: [(4, 4.5), (3, 7.0)],  # Unsorted in map
    }
    kb = FakeKB(linker=linker, skills=skills, related=related)

    profile = {
        "personal_info": {"email": "dev@test.com", "phone": "123"},
        "skills": ["Git"],
    }

    result = enrich(profile, kb)
    related_skills = result["related_skills"]

    # Sorted by weight descending: GitHub (7.0), GitLab (4.5)
    assert len(related_skills) == 2
    assert related_skills[0] == {
        "id": 3,
        "name": "GitHub",
        "category": "Tool",
        "weight": 7.0,
        "via": {"from": "Git", "source": "book"},
    }
    assert related_skills[1] == {
        "id": 4,
        "name": "GitLab",
        "category": "Tool",
        "weight": 4.5,
        "via": {"from": "Git", "source": "book"},
    }


def test_related_skills_excludes_skills_already_in_cv() -> None:
    """Skills already linked in CV are excluded from related_skills."""
    skills = {
        2: ("Git", "Tool"),
        3: ("GitHub", "Tool"),
        4: ("GitLab", "Tool"),
    }
    linker = FakeLinker({
        "Git": Link(raw="Git", skill_id=2, name="Git", category="Tool", method="exact", score=100.0),
        "GitHub": Link(raw="GitHub", skill_id=3, name="GitHub", category="Tool", method="exact", score=100.0),
    })
    related = {
        2: [(3, 7.0), (4, 4.5)],
    }
    kb = FakeKB(linker=linker, skills=skills, related=related)

    profile = {
        "personal_info": {"email": "dev@test.com", "phone": "123"},
        "skills": ["Git", "GitHub"],
    }

    result = enrich(profile, kb)
    related_skills = result["related_skills"]

    # GitHub (id 3) is already in CV, so only GitLab (id 4) is returned
    assert len(related_skills) == 1
    assert related_skills[0]["id"] == 4
    assert related_skills[0]["name"] == "GitLab"


def test_related_skills_dedupes_max_weight_and_caps_at_20() -> None:
    """When multiple CV skills link to same target, keep max weight; cap at 20."""
    skills = {100: ("Git", "Tool"), 200: ("VCS", "Concept")}
    # Generate 25 candidate skills (id 1..25)
    for i in range(1, 26):
        skills[i] = (f"Skill_{i:02d}", "Tech")

    linker = FakeLinker({
        "Git": Link(raw="Git", skill_id=100, name="Git", category="Tool", method="exact", score=100.0),
        "VCS": Link(raw="VCS", skill_id=200, name="VCS", category="Concept", method="exact", score=100.0),
    })

    # Skill 1 is related to both: Git with weight 3.0, VCS with weight 15.0 -> should keep 15.0 via VCS
    related = {
        100: [(1, 3.0)] + [(i, float(i)) for i in range(2, 26)],
        200: [(1, 15.0)],
    }
    kb = FakeKB(linker=linker, skills=skills, related=related)

    profile = {
        "personal_info": {"email": "dev@test.com", "phone": "123"},
        "skills": ["Git", "VCS"],
    }

    result = enrich(profile, kb)
    related_skills = result["related_skills"]

    # Must be capped at 20
    assert len(related_skills) == 20

    # Skill 1 has max weight 15.0 from VCS
    skill_1_matches = [s for s in related_skills if s["id"] == 1]
    assert len(skill_1_matches) == 1
    assert skill_1_matches[0]["weight"] == 15.0
    assert skill_1_matches[0]["via"]["from"] == "VCS"

    # Verify strictly sorted by weight descending
    weights = [s["weight"] for s in related_skills]
    assert weights == sorted(weights, reverse=True)

