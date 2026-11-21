"""Test thư ký chung (kb_pipeline). Dữ liệu ở đây là dữ liệu giả cho test, không phải KB thật."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from kb_pipeline import run, summarize
from kb_pipeline.export import cypher_value, to_cypher
from kb_pipeline.packs import discover, load_pack, validate_pack, write_pack
from kb_pipeline.version import diff, make_version, next_version_id

GROUPS = ["Backend", "Frontend", "Fullstack", "Data"]


def src(sid, trust="medium", publisher=None, kind="pdf"):
    return {"source_id": sid, "type": kind, "title": sid, "publisher": publisher or sid, "trust": trust}


def pack(pid, priority, sources, nodes=(), edges=(), patches=(), origin=None):
    return {"manifest": {"pack_id": pid, "kb_origin": origin or pid.upper(), "priority": priority,
                         "sources": list(sources)},
            "nodes": list(nodes), "edges": list(edges), "patches": list(patches), "sha256": "0" * 64}


def skill(name, type_="technology", aliases=(), amb=(), sources=("P1",), **extra):
    return {"label": "Skill", "name": name, "type": type_, "aliases": list(aliases), "ambiguous_aliases": list(amb),
            "sources": list(sources), **extra}


def ev(sid="P1", quote="x"):
    return [{"source_id": sid, "page": 1, "quote": quote}]


def edge(kind, a, b, sid="P1", **props):
    return {"type": kind, "src": a, "dst": b, "evidence": ev(sid), **props}


BASE = pack("base", 10, [src("P1")],
            nodes=[skill("React", aliases=["reactjs"]), skill("Kubernetes", aliases=["k8s"]),
                   skill("JavaScript", aliases=["js"]), skill("Go", aliases=["golang"], amb=["go"])],
            edges=[edge("USED_IN", "React", "Frontend")])


def by(result, label):
    return {n["key"]: n for n in result["nodes"] if n["label"] == label}


def edges_of(result, kind):
    return {(e["src"], e["dst"]): e for e in result["edges"] if e["type"] == kind}


def test_resolves_by_alias_and_drops_taken_alias():
    """Ví dụ trong thiết kế: gói AI gọi "ReactJS", đề xuất alias "k8s" sai chỗ."""
    ai = pack("ai", 30, [src("G1", "low", kind="generated")],
              nodes=[skill("ReactJS", aliases=["react.js", "k8s"], sources=["G1"])],
              edges=[edge("PARENT_OF", "javascript", "ReactJS", "G1")])
    r = run([BASE, ai], GROUPS)
    assert r["errors"] == []
    skills = by(r, "Skill")
    assert "reactjs" not in skills                                          # không tạo kỹ năng thứ hai
    assert {"react.js", "reactjs"} <= set(skills["react"]["aliases"])
    assert "k8s" in skills["kubernetes"]["aliases"] and "k8s" not in skills["react"]["aliases"]
    conflict = next(x for x in r["review"] if x["kind"] == "alias_conflict")
    assert conflict["alias"] == "k8s" and conflict["owned_by"] == ["kubernetes"]
    assert ("javascript", "react") in edges_of(r, "PARENT_OF")
    assert r["resolved_by_alias"][0]["key"] == "react"


def test_shared_ambiguous_alias_allowed_but_not_free_vs_ambiguous():
    p = pack("p2", 20, [src("P2")], nodes=[skill("Gopher", amb=["go"], sources=["P2"]),
                                           skill("Golang Tool", aliases=["go"], sources=["P2"])])
    r = run([BASE, p], GROUPS)
    skills = by(r, "Skill")
    assert "go" in skills["gopher"]["ambiguous_aliases"]                     # dễ nhầm: được chung
    assert "go" not in skills["golang tool"]["aliases"]                     # thường vs dễ nhầm: bỏ
    assert any(x["kind"] == "alias_conflict" and x["alias"] == "go" for x in r["review"])


def test_unaccented_variants_added():
    p = pack("p2", 20, [src("P2")], nodes=[skill("OOP", type_="concept", aliases=["lập trình hướng đối tượng"],
                                                 sources=["P2"])])
    assert "lap trinh huong doi tuong" in by(run([p], GROUPS), "Skill")["oop"]["aliases"]


def test_new_node_needs_required_fields_and_ref_must_exist():
    p = pack("p2", 20, [src("P2")], nodes=[{"label": "Skill", "name": "NoType", "sources": ["P2"]},
                                           {"label": "Skill", "ref": "ghost", "aliases": ["g"]}])
    kinds = {x["kind"] for x in run([BASE, p], GROUPS)["review"]}
    assert kinds == {"new_node_missing_fields", "unresolved_node"}


def test_value_conflict_trust_wins_and_override():
    hi = pack("hi", 40, [src("H1", "high")], nodes=[skill("React", type_="concept", sources=["H1"])])
    r = run([BASE, hi], GROUPS)
    assert by(r, "Skill")["react"]["type"] == "concept"                     # trust high thắng dù nạp sau
    assert any(x["kind"] == "value_conflict" for x in r["review"])
    cat1 = pack("c1", 10, [src("P1")], nodes=[{"label": "Category", "name": "DBs", "sibling_ok_suggest": False}])
    cat2 = pack("c2", 30, [src("G1", "low", kind="generated")],
                nodes=[{"label": "Category", "name": "DBs", "sibling_ok_suggest": True,
                        "override": ["sibling_ok_suggest"]}])
    r = run([cat1, cat2], GROUPS)
    assert by(r, "Category")["dbs"]["sibling_ok_suggest"] is True
    assert not any(x["kind"] == "value_conflict" for x in r["review"])


def test_patches():
    p = pack("fix", 30, [src("G1", "low", kind="generated")],
             nodes=[skill("Apache React", aliases=["react-apache"], sources=["G1"])],
             edges=[edge("USED_IN", "Apache React", "Backend", "G1")],
             patches=[{"op": "same_as", "label": "Skill", "drop": "apache react", "keep": "react"},
                      {"op": "ambiguous", "label": "Skill", "ref": "js"},
                      {"op": "reject", "label": "Skill", "ref": "kubernetes"},
                      {"op": "set", "label": "Skill", "ref": "golang", "fields": {"type": "concept"}},
                      {"op": "drop_edge", "type": "USED_IN", "src": "react", "dst": "Frontend"},
                      {"op": "reject", "label": "Skill", "ref": "nothing"}])
    r = run([BASE, p], GROUPS)
    skills = by(r, "Skill")
    assert "apache react" not in skills and {"apache react", "react-apache"} <= set(skills["react"]["aliases"])
    assert skills["react"]["merged_from"] == ["apache react"]
    assert ("react", "Backend") in edges_of(r, "USED_IN")                   # quan hệ theo nút đã gộp
    assert ("react", "Frontend") not in edges_of(r, "USED_IN")
    assert skills["javascript"]["aliases"] == [] and "js" in skills["javascript"]["ambiguous_aliases"]
    assert skills["kubernetes"]["status"] == "rejected" and skills["go"]["type"] == "concept"
    assert [x["kind"] for x in r["review"]] == ["unresolved_patch"]


def test_alias_conflict_cleared_by_same_as():
    """Alias thuộc nút sắp bị gộp vào chính nút nhận: không phải trùng."""
    p = pack("fix", 30, [src("G1", "low", kind="generated")],
             nodes=[{"label": "Skill", "ref": "react", "aliases": ["k8s"], "sources": ["G1"]}],
             patches=[{"op": "same_as", "label": "Skill", "drop": "kubernetes", "keep": "react"}])
    r = run([BASE, p], GROUPS)
    assert "k8s" in by(r, "Skill")["react"]["aliases"] and r["review"] == []


def test_edge_rules_type_cycle_unresolved():
    p = pack("p2", 20, [src("P2")],
             nodes=[skill("Agile", type_="concept", sources=["P2"]), skill("A", sources=["P2"]),
                    skill("B", sources=["P2"])],
             edges=[edge("PARENT_OF", "Agile", "React", "P2"),                      # concept làm cha
                    edge("PARENT_OF", "A", "B", "P2"), edge("PARENT_OF", "B", "A", "P2"),   # vòng
                    edge("PARENT_OF", "React", "React", "P2"),                      # tự trỏ
                    edge("USED_IN", "React", "Marketing", "P2"),                    # nhóm không có
                    edge("PARENT_OF", "A", "Ghost", "P2")])
    r = run([BASE, p], GROUPS)
    assert r["errors"] == []
    po = edges_of(r, "PARENT_OF")
    assert po[("agile", "react")]["status"] == "review"
    assert sorted(e["status"] for k, e in po.items() if k in {("a", "b"), ("b", "a")}) in (
        ["candidate", "review"], ["accepted", "review"])
    assert ("react", "react") not in po
    kinds = [x["kind"] for x in r["review"]]
    assert kinds.count("unresolved_edge") == 2 and "parent_of_type" in kinds and "parent_of_cycle" in kinds


def test_scoring_and_status():
    other = pack("o", 20, [src("W1", publisher="other")], edges=[edge("USED_IN", "React", "Frontend", "W1")])
    gen = pack("g", 30, [src("G1", "low", kind="generated"), src("G2", "low", kind="generated")],
               nodes=[skill("Vue", sources=["G1"])],
               edges=[edge("USED_IN", "Vue", "Frontend", "G1"), edge("USED_IN", "Vue", "Frontend", "G2")])
    r = run([BASE, other, gen], GROUPS, policy="rule")
    used = edges_of(r, "USED_IN")
    assert used[("react", "Frontend")]["status"] == "accepted"              # 2 publisher độc lập
    assert used[("react", "Frontend")]["confidence"] == 0.84                 # 1 − 0,4 × 0,4
    assert used[("vue", "Frontend")]["status"] == "candidate"               # nguồn tự sinh không đủ
    skills = by(r, "Skill")
    assert skills["react"]["status"] == "accepted" and skills["vue"]["status"] == "candidate"
    near = [e for e in r["edges"] if e["type"] == "NEAR"]
    assert near == [] or all(e["method"] == "computed" and e["status"] == "candidate" for e in near)


def test_provisional_policy_accepts_all_live_and_marks_it():
    other = pack("o", 20, [src("W1", publisher="other")], edges=[edge("USED_IN", "React", "Frontend", "W1")])
    gen = pack("g", 30, [src("G1", "low", kind="generated")], nodes=[skill("Vue", sources=["G1"])],
               edges=[edge("USED_IN", "Vue", "Frontend", "G1"), edge("USED_IN", "Vue", "Backend", "G1"),
                      edge("USED_IN", "React", "Backend", "G1")])
    r = run([BASE, other, gen], GROUPS, policy="provisional")
    used = edges_of(r, "USED_IN")
    assert used[("react", "Frontend")]["accepted_by"] == "rule"
    assert used[("vue", "Frontend")]["status"] == "accepted"
    assert used[("vue", "Frontend")]["accepted_by"] == "provisional"
    assert by(r, "Skill")["vue"]["accepted_by"] == "provisional"
    assert all(x["status"] != "candidate" for x in [*r["nodes"], *r["edges"]])
    near = {(e["src"], e["dst"]): e for e in r["edges"] if e["type"] == "NEAR" and e["method"] == "computed"}
    assert near[("Backend", "Frontend")]["m"] == 1.0                          # cosine: cùng tập {react, vue}
    cat = pack("c", 40, [src("C1")], nodes=[{"label": "Category", "name": "DBs", "sibling_ok_suggest": True,
                                              "sources": ["C1"]}])
    c = by(run([cat], GROUPS, policy="provisional"), "Category")["dbs"]
    assert c["sibling_ok"] is True and c["sibling_ok_by"] == "provisional"
    assert by(run([cat], GROUPS, policy="rule"), "Category")["dbs"].get("sibling_ok") is None


def test_near_hypothesis_symmetric_and_merged():
    a = pack("a", 10, [src("P1")], edges=[edge("NEAR", "Fullstack", "Backend", method="hypothesis", m=0.8)])
    b = pack("b", 20, [src("P2")], edges=[edge("NEAR", "Backend", "Fullstack", "P2", method="hypothesis", m=0.8)])
    r = run([a, b], GROUPS)
    hyp = [e for e in r["edges"] if e["type"] == "NEAR" and e["method"] == "hypothesis"]
    assert len(hyp) == 1 and (hyp[0]["src"], hyp[0]["dst"]) == ("Backend", "Fullstack")
    assert hyp[0]["sources"] == ["P1", "P2"]


def test_validation_blocks_bad_pack():
    bad = pack("bad", 10, [src("P1")], nodes=[{"label": "Skil", "name": "x"}, skill("Y", type_="tool")],
               edges=[{"type": "PARENT_OF", "src": "a", "dst": "b", "evidence": []},
                      edge("USED_IN", "a", "b", "P9")],
               patches=[{"op": "explode"}])
    assert len(validate_pack(bad)) >= 5
    assert run([bad], GROUPS)["errors"]


def test_source_id_must_be_unique_across_packs():
    a = pack("a", 10, [src("P1")])
    b = pack("b", 20, [src("P1", "high")])
    assert any("P1" in e for e in run([a, b], GROUPS)["errors"])


def test_write_and_discover(tmp_path):
    write_pack("z-pack", "KBZ", 50, [src("P1")], [skill("React")], [edge("USED_IN", "React", "Frontend")],
               packs_dir=tmp_path)
    write_pack("a-pack", "KBA", 5, [src("P2")], [skill("Vue", sources=["P2"])], [], packs_dir=tmp_path)
    found = discover(tmp_path)
    assert [p["manifest"]["pack_id"] for p in found] == ["a-pack", "z-pack"]   # theo priority
    assert load_pack(tmp_path / "z-pack")["nodes"][0]["name"] == "React"


def test_diff_and_version():
    r1 = run([BASE], GROUPS)
    p = pack("ai", 30, [src("G1", "low", kind="generated")], nodes=[skill("Vue", sources=["G1"])])
    r2 = run([BASE, p], GROUPS)
    d = diff(r1["nodes"], r1["edges"], r2["nodes"], r2["edges"])
    assert d["summary"]["nodes"]["added"] == {"Skill": 1, "Source": 1} and not d["empty"]
    v1, new1 = make_version([], r1["nodes"], r1["edges"], [BASE], diff([], [], r1["nodes"], r1["edges"]), [])
    assert new1 and v1["previous"] is None
    same, new_again = make_version([v1], r1["nodes"], r1["edges"], [BASE],
                                   diff(r1["nodes"], r1["edges"], r1["nodes"], r1["edges"]), r1["nodes"])
    assert not new_again and same is v1
    v2, _ = make_version([v1], r2["nodes"], r2["edges"], [BASE, p], d, r1["nodes"])
    assert v2["previous"] == v1["id"] and v2["sources_changed"] == ["G1"] and v2["id"] != v1["id"]
    assert next_version_id([{"id": "kb-2026-01-01"}], __import__("datetime").date(2026, 1, 1)) == "kb-2026-01-01-2"


def test_cypher_value_and_script():
    assert cypher_value({"a": "it's \\ ok", "b": [1, 2.5, None, True]}) == "{`a`: 'it\\'s \\\\ ok', `b`: [1, 2.5, null, true]}"
    r = run([BASE], GROUPS)
    version = {"id": "kb-x", "created": "now"}
    text = to_cypher(r["nodes"], r["edges"], version, GROUPS, summarize(r))
    stmts = [line for line in text.splitlines() if line and not line.startswith("//")]
    assert all(s.endswith(";") and "$rows" not in s for s in stmts)
    assert any(s.startswith("UNWIND [{`key`: 'go'") and "MERGE (x:Skill" in s for s in stmts)
    assert any("MERGE (a)-[e:USED_IN]->(b)" in s for s in stmts)
    assert any("MERGE (v:KBVersion" in s for s in stmts)
