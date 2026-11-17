"""Test hàm thuần của export_snapshot.py (không cần Neo4j)."""
from export_snapshot import assign_skill_ids, build_snapshot


def data(**over):
    base = {
        "skills": [
            {"key": "java", "name": "java", "type": "technology", "aliases": ["java", "core java"],
             "ambiguous_aliases": [], "status": "candidate", "n_evidence": 2},
            {"key": "spring boot", "name": "Spring Boot", "type": "technology", "aliases": ["springboot"],
             "ambiguous_aliases": ["spring"], "status": "candidate", "n_evidence": 1},
            {"key": "go", "name": "Go", "type": "technology", "aliases": ["golang"],
             "ambiguous_aliases": ["go"], "status": "accepted", "n_evidence": 1},
            {"key": "javascript", "name": "javascript", "type": "technology", "aliases": ["js", "javascript"],
             "ambiguous_aliases": [], "status": "candidate", "n_evidence": 0},
            {"key": "mysql", "name": "MySQL", "type": "technology", "aliases": ["mysql"],
             "ambiguous_aliases": [], "status": "candidate", "n_evidence": 1},
            {"key": "postgresql", "name": "PostgreSQL", "type": "technology", "aliases": ["postgres"],
             "ambiguous_aliases": [], "status": "candidate", "n_evidence": 1},
        ],
        "parent_of": [{"parent": "java", "child": "spring boot", "status": "candidate"}],
        "in_category": [
            {"skill": "mysql", "category": "relational databases", "status": "candidate", "sibling_ok": None,
             "sibling_ok_suggest": True, "category_status": "candidate"},
            {"skill": "postgresql", "category": "relational databases", "status": "candidate", "sibling_ok": None,
             "sibling_ok_suggest": True, "category_status": "candidate"},
            {"skill": "java", "category": "programming languages", "status": "candidate", "sibling_ok": None,
             "sibling_ok_suggest": False, "category_status": "candidate"},
        ],
        "titles": [
            {"key": "backend developer", "name": "Backend Developer", "aliases": ["lập trình viên backend"],
             "status": "candidate", "groups": [{"group": "Backend", "status": "candidate"}]},
            {"key": "data scientist", "name": "Data Scientist", "aliases": [], "status": "candidate",
             "groups": [{"group": "AI/ML", "status": "candidate"}, {"group": "Data", "status": "candidate"}]},
            {"key": "ba", "name": "Business Analyst", "aliases": [], "status": "candidate", "groups": []},
        ],
        "levels": [{"key": "senior", "name": "Senior", "rank": 4, "aliases": ["sr", "senior"], "status": "candidate"}],
        "majors": [{"key": "se", "name": "Software Engineering", "group": "it", "aliases": ["kỹ thuật phần mềm"],
                    "status": "candidate"}],
        "near": [{"a": "Backend", "b": "Fullstack", "m": 0.038, "method": "computed", "status": "candidate"}],
    }
    base.update(over)
    return base


def ids_for(d):
    return assign_skill_ids([s["key"] for s in d["skills"]], {})


def test_assign_skill_ids_stable():
    first = assign_skill_ids(["b", "a"], {})
    assert first == {"a": "S0001", "b": "S0002"}
    again = assign_skill_ids(["a", "b", "c"], {"a": "S0001", "b": "S0002", "gone": "S0007"})
    assert again["a"] == "S0001" and again["c"] == "S0008"   # không cấp lại mã đã dùng


def test_build_snapshot_rows():
    d = data()
    ids = ids_for(d)
    rows, rep = build_snapshot(d, ids)
    sk = {r["name"]: r for r in rows["skill_ontology"]}
    assert sk["Spring Boot"]["parents"] == [ids["java"]]
    assert sk["MySQL"]["categories_sibling_ok"] == ["relational databases"]   # dev: dùng sibling_ok_suggest
    assert sk["java"]["categories_sibling_ok"] == []
    assert "go" in sk["Go"]["aliases"]                                         # dễ nhầm 1 chủ -> vẫn là alias
    amb = {r["alias"]: r["candidates"] for r in rows["ambiguous_aliases"]}
    assert amb["go"] == [ids["go"]] and amb["spring"] == [ids["spring boot"]]
    assert amb["js"] == [ids["javascript"]] and "sr" not in amb               # alias skill ngắn -> dễ nhầm
    t = {r["alias"]: r for r in rows["role_title_map"]}
    assert t["backend developer"]["role_group"] == "Backend"
    assert t["lập trình viên backend"]["role_group"] == "Backend"
    assert t["data scientist"]["role_group"] == "Data"                        # nhiều nhóm -> theo thứ tự ROLE_GROUPS
    assert t["sr"] == {"kind": "level", "alias": "sr", "level_rank": 4}
    assert rows["major_group"][0] == {"major_alias": "kỹ thuật phần mềm", "group": "it"}
    methods = {(r["group_a"], r["group_b"], r["method"]) for r in rows["role_distance"]}
    assert ("Backend", "Fullstack", "hypothesis") in methods and ("Backend", "Fullstack", "computed") in methods
    assert rep["blocking"] == {"alias_conflicts": {}, "parent_cycles": []}
    assert rep["warnings"]["job_titles_without_role_group"] == 1
    assert rep["warnings"]["skills_without_evidence"] == 1
    assert rep["warnings"]["job_titles_multi_group"][0]["chosen"] == "Data"


def test_accepted_only_filters():
    d = data()
    rows, rep = build_snapshot(d, ids_for(d), include_candidate=False)
    assert [r["name"] for r in rows["skill_ontology"]] == ["Go"]
    assert rows["role_title_map"] == []


def test_blocking_alias_conflict_and_cycle():
    d = data()
    d["skills"][4]["aliases"] = ["mysql", "postgres"]                         # trùng alias của PostgreSQL
    d["parent_of"].append({"parent": "spring boot", "child": "java", "status": "candidate"})
    _, rep = build_snapshot(d, ids_for(d))
    assert "postgres" in rep["blocking"]["alias_conflicts"]
    assert rep["blocking"]["parent_cycles"]
