"""Test các hàm thuần của pipeline. Dữ liệu ở đây là dữ liệu giả cho test, không phải KB thật."""
import pathlib
import sys

import pymupdf
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from kb1.pipeline.s2_nodes import drop_overdrawn, is_noise, is_prose, merge_lines
from kb1.pipeline.s3_groups import edge_dist, pick_heading
from kb1.pipeline.s4_classify import rule_type, validate
from kb1.pipeline.s5_triples import alias_conflicts, build, find_cycle, is_parent_of
from kb1.pipeline.so_aliases import apply_so_aliases, classify, is_version
from kb2.pipeline.s1_crawl_itviec import parse_titles
from kb2.pipeline.s2_titles import build_titles
from kb2.pipeline.s3_majors import build_majors, strip_accents
from kb2.pipeline.s4_levels import build_levels
from load_kb import flatten_evidence, merge_kb, near_edges
from shared.common import norm


def rect_node(x0, y0, x1, y1, **extra):
    return {"rect": pymupdf.Rect(x0, y0, x1, y1), **extra}


def test_norm():
    assert norm("  Spring   BOOT\n") == "spring boot"


def test_edge_dist():
    a = pymupdf.Rect(0, 0, 10, 10)
    assert edge_dist(a, pymupdf.Rect(5, 5, 20, 20)) == 0
    assert edge_dist(a, pymupdf.Rect(13, 14, 20, 20)) == 5


def test_noise_and_prose():
    assert is_noise("Scrimba is offering 20% off to roadmap users")
    assert is_noise("Python Roadmap")
    assert not is_noise("Pinecone")
    assert not is_prose("Advanced Crypto.")
    assert is_prose("Use the checkpoints and do not forget to practice.")


def test_drop_overdrawn():
    span = {"rect": pymupdf.Rect(10, 10, 50, 20), "text": "Tools", "size": 10}
    other = {"rect": pymupdf.Rect(10, 200, 50, 210), "text": "Tools", "size": 10}
    assert len(drop_overdrawn([span, dict(span), other])) == 2


def test_merge_lines_keeps_columns_apart():
    spans = [{"rect": pymupdf.Rect(0, 0, 50, 10), "text": "Find the", "size": 10},
             {"rect": pymupdf.Rect(0, 12, 50, 22), "text": "detailed version", "size": 10},
             {"rect": pymupdf.Rect(100, 0, 150, 10), "text": "Other", "size": 10}]
    assert sorted(m["text"] for m in merge_lines(spans)) == ["Find the detailed version", "Other"]


def test_pick_heading_side_by_side():
    layouts = rect_node(70, 540, 110, 553, label="Layouts")
    elements = rect_node(260, 540, 310, 553, label="Elements")
    sub = rect_node(243, 565, 300, 590, group_bottom=590)
    assert pick_heading(sub, [layouts, elements]) is elements


def test_pick_heading_footer():
    first = rect_node(0, 100, 50, 110, label="Understanding")
    last = rect_node(0, 300, 50, 310, label="Best Practices")
    sub = rect_node(0, 200, 50, 220, group_bottom=310)
    assert pick_heading(sub, [first, last]) is last


def test_rule_type():
    assert rule_type("What is an AI Engineer?") == "not_skill"
    assert rule_type("RAG vs Fine-tuning") == "not_skill"
    assert rule_type("Pinecone") is None


def test_validate_reports_missing_and_bad_type():
    result = {"items": [{"id": "0", "type": "technology"}, {"id": "1", "type": "framework"}]}
    ok, missing = validate(["0", "1", "2"], result)
    assert set(ok) == {"0"}
    assert missing == {"1", "2"}


def test_is_parent_of():
    assert is_parent_of("ollama", "ollama sdk")
    assert is_parent_of("java", "spring boot")
    assert not is_parent_of("go", "go")
    assert not is_parent_of("redis", "kafka")


def test_find_cycle():
    assert find_cycle([{"type": "PARENT_OF", "src": "a", "dst": "b"}]) is None
    assert find_cycle([{"type": "PARENT_OF", "src": "a", "dst": "b"},
                       {"type": "PARENT_OF", "src": "b", "dst": "a"}])


def test_flatten_evidence():
    edge = {"type": "X", "evidence": [{"source_id": "P01", "page": 1, "quote": "a > b"}]}
    assert isinstance(flatten_evidence(edge)["evidence"][0], str)


def fixture():
    def node(i, label, kind, pdf="ai-engineer"):
        return {"pdf": pdf, "page": 1, "node_id": f"{pdf}#{i}", "label": label, "kind": kind}

    def row(child, cid, parent, pick=False, pdf="ai-engineer"):
        return {"pdf": pdf, "child": child, "child_id": f"{pdf}#{cid}", "child_kind": "sub",
                "parent": parent, "pick_one": pick}

    def label(text, kind):
        return {"key": norm(text), "label": text, "type": kind, "canonical": text}

    nodes = [node(1, "Pinecone", "sub"), node(2, "Chroma", "sub"), node(3, "Ollama", "main"),
             node(4, "Ollama SDK", "sub"), node(5, "Docker", "sub", pdf="devsecops")]
    groups = [row("Pinecone", 1, "Vector DBs (pick one)", pick=True),
              row("Chroma", 2, "Vector DBs (pick one)", pick=True),
              row("Ollama SDK", 4, "Ollama")]
    labels = [label("Pinecone", "technology"), label("Chroma", "technology"),
              label("Ollama", "technology"), label("Ollama SDK", "technology"),
              label("Docker", "technology"), label("Vector DBs (pick one)", "category")]
    sources = [{"source_id": "P01", "uri": "data/pdf/ai-engineer.pdf"},
               {"source_id": "P10", "uri": "data/pdf/devsecops.pdf"}]
    return nodes, groups, labels, sources


def test_build_nodes_and_edges():
    kb_nodes, edges, checks = build(*fixture())
    skills = {n["key"] for n in kb_nodes if n["label"] == "Skill"}
    assert skills == {"pinecone", "chroma", "ollama", "ollama sdk", "docker"}
    category = next(n for n in kb_nodes if n["label"] == "Category")
    assert category["sibling_ok_suggest"] is True

    found = {(e["type"], e["src"], e["dst"]) for e in edges}
    assert ("IN_CATEGORY", "pinecone", "vector dbs (pick one)") in found
    assert ("PARENT_OF", "ollama", "ollama sdk") in found
    assert ("USED_IN", "pinecone", "AI/ML") in found
    assert ("USED_IN", "pinecone", "Data") not in found
    assert ("USED_IN", "docker", "DevOps") in found      # một roadmap, hai nhóm vai trò
    assert ("USED_IN", "docker", "Security") in found
    assert ("EVIDENCED_BY", "pinecone", "P01") in found
    assert checks["alias_conflicts"] == {} and checks["parent_of_cycle"] is None


def test_build_moves_ambiguous_alias():
    nodes, groups, labels, sources = fixture()
    nodes.append({"pdf": "ai-engineer", "page": 1, "node_id": "ai-engineer#9", "label": "Go", "kind": "sub"})
    labels.append({"key": "go", "label": "Go", "type": "technology", "canonical": "Go"})
    kb_nodes, _, checks = build(nodes, groups, labels, sources)
    go = next(n for n in kb_nodes if n.get("key") == "go")
    assert go["aliases"] == [] and go["ambiguous_aliases"] == ["go"]
    assert checks["ambiguous_aliases"] == {"go": ["go"]}


def skill(key, aliases=None, ambiguous=None):
    return {"label": "Skill", "key": key, "name": key, "type": "technology",
            "aliases": aliases if aliases is not None else [key], "ambiguous_aliases": ambiguous or []}


def so_rows(*pairs):
    return [{"synonym": s, "target": t} for s, t in pairs]


def test_is_version():
    for tag, target in [("python-3.11", "python"), ("angular4", "angular"), ("pandas-2.x", "pandas"),
                        ("neo4j2.0", "neo4j"), ("sql-server-vnext", "sql-server"), ("angularjs2", "angular")]:
        assert is_version(tag, target), tag
    for tag, target in [("ec2", "amazon-ec2"), ("oauth2", "oauth-2.0"), ("k8s", "kubernetes")]:
        assert not is_version(tag, target), tag


def test_classify():
    assert classify("k8s", "kubernetes", "kubernetes")[0] == "alias"
    assert classify("vue-js", "vue.js", "vue.js")[0] == "alias"
    assert classify("apache-solr", "solr", "solr")[0] == "alias"
    assert classify("unit-tests", "unit-testing", "unit testing")[0] == "alias"
    assert classify("py", "python", "python")[0] == "ambiguous"
    for tag, target in [("css-border-radius", "css"), ("div", "html"), ("points", "point"),
                        (".java", "java"), ("php5", "php")]:
        assert classify(tag, target, target)[0] == "drop", tag


def test_apply_so_aliases():
    nodes = [skill("kubernetes"), skill("rest"), skill("python"), skill("react"), skill("airflow"),
             skill("apache airflow"), {"label": "Category", "key": "tools", "name": "Tools"}]
    rows = so_rows(("k8s", "kubernetes"), ("rest-api", "rest"), ("py", "python"), ("python-3.11", "python"),
                   ("apache-airflow", "airflow"), ("react.js", "reactjs"), ("not-a-skill", "unknown-tag"))
    report, counts = apply_so_aliases(nodes, rows)
    by_key = {n["key"]: n for n in nodes}
    assert "k8s" in by_key["kubernetes"]["aliases"]
    assert {"rest-api", "rest api"} <= set(by_key["rest"]["aliases"])       # giữ cả dạng có dấu cách
    assert by_key["python"]["ambiguous_aliases"] == ["py"] and "py" not in by_key["python"]["aliases"]
    assert not any("3.11" in a for a in by_key["python"]["aliases"])
    assert {"react.js", "reactjs"} <= set(by_key["react"]["aliases"])       # qua SO_BRIDGE
    assert by_key["airflow"]["aliases"] == ["airflow"]                     # alias không chia cho hai kỹ năng
    assert counts["conflict"] == 1 and counts["not_in_kb"] == 1
    assert alias_conflicts(nodes) == {}
    assert all(r["synonym"] != "not-a-skill" for r in report)


def title_row(group, vi, en, canonical="", roles="", aliases=""):
    return {"group": group, "name_vi": vi, "name_en": en, "canonical": canonical, "role_groups": roles,
            "aliases": aliases}


def raw_title(lang, group, name):
    return {"lang": lang, "group": group, "name": name, "url": "/x"}


def test_parse_titles():
    page = """<h1 class='job-expertise-index-headline'>x</h1>
    <div class='h2 head-divider-text fw-bold'>Web &amp; App</div>
    <a class="skill-tag-link normal-text" href="/viec-lam-it/be">Lập trình viên Backend
    </a>"""
    assert parse_titles(page, "vi") == [{"lang": "vi", "group": "Web & App", "name": "Lập trình viên Backend",
                                         "url": "/viec-lam-it/be"}]


def test_build_titles():
    raw = [raw_title("vi", "G", "Lập trình viên Backend"), raw_title("en", "G", "Backend Developer"),
           raw_title("vi", "G", "Quản lý"), raw_title("en", "G", "Manager")]
    mapping = [title_row("G", "Lập trình viên Backend", "Backend Developer", roles="Backend"),
               title_row("G", "Quản lý", "Manager", canonical="IT Manager", aliases="manager")]
    nodes, edges, checks = build_titles(raw, mapping, {"source_id": "W01"})
    backend = next(n for n in nodes if n.get("key") == "backend developer")
    assert backend["name"] == "Backend Developer" and "lập trình viên backend" in backend["aliases"]
    manager = next(n for n in nodes if n.get("key") == "it manager")
    assert set(manager["ambiguous_aliases"]) == {"manager", "quản lý"}
    assert [(e["src"], e["dst"]) for e in edges] == [("backend developer", "Backend")]
    assert checks["titles_without_role_group"] == ["it manager"] and checks["alias_conflicts"] == {}


def test_build_titles_rejects_wrong_pair():
    raw = [raw_title("vi", "G", "Quản lý"), raw_title("en", "G", "Manager")]
    with pytest.raises(SystemExit):
        build_titles(raw, [title_row("G", "Quản lý", "Vice President")], {"source_id": "W01"})
    with pytest.raises(SystemExit):
        build_titles(raw, [title_row("G", "Quản lý", "Manager", roles="Management")], {"source_id": "W01"})


def test_merge_kb():
    source = {"label": "Source", "source_id": "P01"}
    kb1 = ([skill("java"), source],
           [{"type": "EVIDENCED_BY", "src": "java", "dst": "P01", "sources": ["P01"], "evidence": []}])
    title = {"label": "JobTitle", "key": "java developer", "aliases": ["java dev"], "ambiguous_aliases": []}
    kb2 = ([title, {**skill("java", ["java", "java se"])}],
           [{"type": "MAPS_TO", "src": "java developer", "dst": "Backend", "sources": ["W01"], "evidence": []}])
    nodes, edges, checks = merge_kb({"KB1": kb1, "KB2": kb2})
    java = next(n for n in nodes if n.get("key") == "java")
    assert java["aliases"] == ["java", "java se"] and java["kb_origin"] == ["KB1", "KB2"]
    assert next(n for n in nodes if n["label"] == "JobTitle")["kb_origin"] == ["KB2"]
    assert len(edges) == 2 and checks["dangling_edges"] == [] and checks["alias_conflicts"] == {}
    assert checks["job_titles_without_role_group"] == 0


def test_merge_kb_reports_problems():
    edge = {"type": "MAPS_TO", "src": "ghost", "dst": "Backend", "sources": [], "evidence": []}
    nodes = [skill("a", ["same"]), skill("b", ["same"])]
    _, _, checks = merge_kb({"KB1": (nodes, [edge])})
    assert checks["dangling_edges"] == [["MAPS_TO", "ghost", "Backend"]]
    assert checks["alias_conflicts"] == {"Skill: same": ["a", "b"]}


def used_in(skill_key, group):
    return {"type": "USED_IN", "src": skill_key, "dst": group, "sources": ["P01"], "evidence": []}


def test_near_edges():
    edges = [used_in("java", "Backend"), used_in("sql", "Backend"), used_in("sql", "Data"), used_in("css", "Frontend")]
    near = {(e["src"], e["dst"]): e for e in near_edges(edges)}
    assert set(near) == {("Backend", "Frontend"), ("Backend", "Data"), ("Frontend", "Data")}   # lưu một chiều
    assert near[("Backend", "Data")]["m"] == 0.5 and near[("Backend", "Data")]["shared_skills"] == 1
    assert near[("Backend", "Frontend")]["m"] == 0 and near[("Backend", "Data")]["method"] == "computed"


def major_row(en, vi, group="it", aliases=""):
    return {"name_en": en, "name_vi": vi, "group": group, "aliases": aliases}


def test_strip_accents():
    assert strip_accents("kỹ thuật điện tử") == "ky thuat dien tu"


def test_build_majors():
    nodes = build_majors([major_row("Information Technology", "Công nghệ thông tin", aliases="it|cntt")],
                         {"source_id": "M01"})
    major = nodes[0]
    assert major["key"] == "information technology" and major["group"] == "it"
    assert {"công nghệ thông tin", "cong nghe thong tin", "cntt"} <= set(major["aliases"])
    assert major["ambiguous_aliases"] == ["it"] and nodes[1]["label"] == "Source"


def test_build_majors_rejects_bad_rows():
    with pytest.raises(SystemExit):
        build_majors([major_row("Law", "Luật", group="legal")], {"source_id": "M01"})
    with pytest.raises(SystemExit):
        build_majors([major_row("A", "Chung"), major_row("B", "Chung")], {"source_id": "M01"})


def level_rows():
    names = ["Intern", "Fresher", "Junior", "Mid", "Senior", "Lead"]
    return [{"name": n, "rank": str(i), "aliases": ""} for i, n in enumerate(names)]


def test_build_levels():
    rows = level_rows()
    rows[2]["aliases"] = "jr|nhân viên"
    rows[5]["aliases"] = "tech lead|trưởng nhóm"
    nodes = build_levels(rows, {"source_id": "M02"})
    junior = next(n for n in nodes if n.get("key") == "junior")
    assert junior["rank"] == 2 and "jr" in junior["aliases"]
    assert junior["ambiguous_aliases"] == ["nhan vien", "nhân viên"]
    lead = next(n for n in nodes if n.get("key") == "lead")
    assert lead["ambiguous_aliases"] == ["lead"] and {"tech lead", "truong nhom"} <= set(lead["aliases"])


def test_build_levels_rejects_wrong_scale():
    rows = level_rows()
    rows[4]["rank"] = "9"
    with pytest.raises(SystemExit):
        build_levels(rows, {"source_id": "M02"})
    rows = level_rows()
    rows[0]["aliases"] = rows[1]["aliases"] = "chung"
    with pytest.raises(SystemExit):
        build_levels(rows, {"source_id": "M02"})
