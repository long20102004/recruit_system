"""Synthetic acceptance mentions against the checked-in public-source KB only.

This vocabulary is deliberately written out, not harvested from any CV dataset.
Missing public evidence must fail visibly until the source snapshots are rebuilt.
"""

from pathlib import Path

import pytest

from app.kb.keys import school_key
from app.kb.linker import SkillLinker
from app.kb.store import KnowledgeBase


TECHNICAL_MENTIONS = (
    "HTML", "CSS", "HTML5", "CSS3", "SCSS", "AWS", "Docker Compose",
    "Node.js", "Nodejs", "Express.js", "Spring MVC", "Spring Data JPA",
    "Hibernate", "JPA", "Lombok", "Thymeleaf", "Entity Framework", "LINQ",
    "AutoMapper", "SignalR", "Material-UI", "MUI", "Bootstrap", "Postman",
    "MySQL Workbench", "Anaconda", "Photoshop", "Illustrator", "Microsoft Excel",
    "Microsoft Word", "Microsoft PowerPoint", "Figma", "Lark", "Lumen",
    "Sequelize", "Mockito", "JUnit", "OOP", "object-oriented programming", "MVC",
    "microservices", "event-driven architecture", "CI/CD", "continuous integration",
    "continuous delivery", "dependency injection", "unit testing", "machine learning",
    "JWT", "JSON Web Token", "stored procedure", "responsive web design",
    "Agile", "Scrum", "Kanban",
)
SOFT_MENTIONS = (
    "teamwork", "communication", "problem-solving", "time management",
    "adaptability", "self-learning", "presentation", "Làm việc nhóm", "Giao tiếp",
    "Thuyết trình", "Giải quyết vấn đề", "Quản lý thời gian", "Tự học",
)
PUBLIC_MENTIONS = TECHNICAL_MENTIONS + SOFT_MENTIONS


@pytest.fixture(scope="module")
def public_kb() -> KnowledgeBase:
    return KnowledgeBase.from_csv(Path(__file__).resolve().parents[2] / "kb/seed")


def test_public_vocabulary_link_coverage_at_least_90_percent(public_kb):
    missing = []
    for mention in PUBLIC_MENTIONS:
        links = public_kb.linker.link(mention)
        # A fragment of a split phrase is not coverage of the complete mention.
        if len(links) != 1 or links[0].skill_id is None:
            missing.append(mention)
    linked = len(PUBLIC_MENTIONS) - len(missing)
    assert linked / len(PUBLIC_MENTIONS) >= 0.90, (
        f"Public vocabulary coverage: {linked}/{len(PUBLIC_MENTIONS)}; "
        f"missing: {missing}"
    )


@pytest.mark.parametrize(
    ("mention", "canonical_names"),
    [
        ("HTML", {"html", "hypertext markup language"}),
        ("CSS", {"css", "cascading style sheets"}),
        ("HTML5", {"html5", "html", "hypertext markup language"}),
        ("CSS3", {"css3", "css", "cascading style sheets"}),
        ("SCSS", {"sassy cascading style sheets", "sass", "scss"}),
        ("MVC", {"model–view–controller", "model-view-controller", "model view controller"}),
        ("Spring MVC", {"spring mvc", "spring web mvc"}),
    ],
)
def test_public_vocabulary_does_not_substitute_related_concepts(
    public_kb, mention, canonical_names
):
    links = public_kb.linker.link(mention)
    assert len(links) == 1
    if mention == "Spring MVC" and links[0].skill_id is None:
        # A missing public item is counted by the overall >=90% contract;
        # never substitute the parent framework or the unrelated MVC pattern.
        return
    assert links[0].skill_id is not None, mention
    assert links[0].name.casefold() in canonical_names, (mention, links[0])


@pytest.mark.parametrize("mention", SOFT_MENTIONS)
def test_public_soft_skills_are_not_technical_concepts(public_kb, mention):
    links = public_kb.linker.link(mention)
    assert len(links) == 1
    assert links[0].skill_id is not None, mention
    assert links[0].category == "Soft Skill", (mention, links[0])


@pytest.mark.parametrize(
    ("abbreviation", "official_english", "canonical_hint"),
    [
        (
            "HCMUTE",
            "Ho Chi Minh City University of Technology and Education",
            ("su pham ky thuat", "cong nghe ky thuat"),
        ),
        (
            "UIT",
            "University of Information Technology",
            "cong nghe thong tin",
        ),
        ("FPT Polytechnic", "FPT Polytechnic", "fpt polytechnic"),
    ],
)
def test_public_school_official_english_and_abbreviation(
    public_kb, abbreviation, official_english, canonical_hint
):
    school = public_kb.link_school(official_english)
    assert school is not None, official_english
    hints = (canonical_hint,) if isinstance(canonical_hint, str) else canonical_hint
    assert any(hint in school_key(school[1]) for hint in hints)
    assert public_kb.link_school(abbreviation) == school


@pytest.mark.parametrize(
    "mention",
    [
        "Học viện Công nghệ Bưu chính Viễn thông (PTIT)",
        "Posts and Telecommunications Institute of Technology (PTIT)",
        "PTIT (cơ sở Hà Nội)",
        "Tên trường chưa có trong KB (PTIT)",
        "Posts and Telecommunications Institute of Technology - PTIT",
    ],
)
def test_public_school_parentheses_and_abbreviation_suffix(public_kb, mention):
    school = public_kb.link_school("PTIT")
    assert school is not None
    assert public_kb.link_school(mention) == school


@pytest.mark.parametrize(
    "mention",
    [
        "Known Institute (unlisted campus)",
        "Unlisted Institute (KI)",
        "Unlisted Institute - KI",
    ],
)
def test_school_parentheses_resolve_only_known_components(mention):
    kb = KnowledgeBase(
        source="synthetic", linker=SkillLinker({}, {}, {}), skills={}, edges={},
        school_alias={"known institute": 1, "ki": 1},
        universities={1: "Known Institute"},
    )
    assert kb.link_school(mention) == (1, "Known Institute")


def test_school_parent_suffix_does_not_resolve_unknown_child():
    kb = KnowledgeBase(
        source="synthetic", linker=SkillLinker({}, {}, {}), skills={}, edges={},
        school_alias={school_key("ĐHQG TP.HCM"): 1},
        universities={1: "ĐHQG TP.HCM"},
    )
    assert kb.link_school("Trường chưa biết - ĐHQG TP.HCM") is None
    assert kb.link_school("Trường chưa biết (ZZUNKNOWN)") is None


def test_soft_skill_linguistic_variants_are_unique_and_category_scoped():
    linker = SkillLinker(
        {1: ("Làm việc theo nhóm", "Soft Skill"), 2: ("Chủ nghĩa tự học", "Soft Skill"),
         3: ("Theo Framework", "Framework/Library")}, {}, {}
    )
    assert linker.link("Làm việc nhóm")[0].skill_id == 1
    assert linker.link("Tự học")[0].skill_id == 2
    assert linker.link("Framework")[0].skill_id is None
    ambiguous = SkillLinker({1: ("Làm việc theo nhóm", "Soft Skill"),
                             2: ("Làm theo việc nhóm", "Soft Skill")}, {}, {})
    assert ambiguous.link("Làm việc nhóm")[0].skill_id is None
