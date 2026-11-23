"""System extension: interview skills and family relations sit on the public seed."""

from pathlib import Path

from app.kb.store import KnowledgeBase
from app.kg.enrich import enrich

SEED = Path(__file__).resolve().parents[1] / "kb" / "seed"


def test_rest_and_security_resolve_and_spring_boot_still_requires_java():
    kb = KnowledgeBase.from_csv(SEED)
    rest = kb.linker.link_many(["RESTful"])[0]
    security = kb.linker.link_many(["bảo mật"])[0]
    assert rest.name == "REST API"
    assert security.name == "Security"
    spring = next(sid for sid, (name, _) in kb.skills.items() if name == "Spring Boot")
    java = next(sid for sid, (name, _) in kb.skills.items() if name == "Java")
    assert ("REQUIRES", java) in kb.edges[spring]
    react = next(sid for sid, (name, _) in kb.skills.items() if name == "React")
    frontend = next(sid for sid, (name, _) in kb.skills.items() if name == "Frontend Framework")
    assert ("IS_A", frontend) in kb.edges[react]


def test_implied_skills_follow_requires_not_family_labels():
    kb = KnowledgeBase.from_csv(SEED)
    result = enrich({"skills": ["Spring Boot"]}, kb)
    assert "Java" in [item["name"] for item in result["implied_skills"]]
    assert "Web Framework" not in [item["name"] for item in result["implied_skills"]]
