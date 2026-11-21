"""Test adapter KB3 và adapter đóng gói KB1, KB2. Dữ liệu ở đây là dữ liệu giả cho test."""
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from kb1.pipeline.s7_pack import to_pack as kb1_to_pack
from kb2.pipeline.s5_pack import to_pack as kb2_to_pack
from kb3.pipeline.build import build
from kb_pipeline import run
from kb_pipeline.packs import validate_pack

HEADERS = {
    "new_skills": "name,type,aliases,ambiguous_aliases,categories,parents,role_groups",
    "skill_aliases": "key,aliases,ambiguous_aliases",
    "skill_fixes": "op,key,value,reason",
    "edges": "type,src,dst,note",
    "categories": "name,sibling_ok,note",
    "titles": "name,aliases,ambiguous_aliases,role_groups",
    "levels": "name,aliases,ambiguous_aliases",
    "majors": "name_en,name_vi,group,aliases",
    "near": "group_a,group_b,m,note",
}
G_SOURCES = [{"source_id": f"G0{i}", "type": "generated", "title": "t", "publisher": "Claude", "trust": "low"}
             for i in range(1, 10)]


def tables(**lines):
    out = {}
    for name, header in HEADERS.items():
        rows = lines.get(name, [])
        parsed = list(csv.DictReader([header, *rows]))
        out[name] = [(i + 2, rows[i], parsed[i]) for i in range(len(rows))]
    return out


def kb3_pack(**lines):
    nodes, edges, patches = build(tables(**lines))
    return {"manifest": {"pack_id": "kb3", "kb_origin": "KB3", "priority": 30, "sources": G_SOURCES},
            "nodes": nodes, "edges": edges, "patches": patches, "sha256": "0"}


def test_kb3_build_is_valid_pack_and_merges_by_name():
    base = {"manifest": {"pack_id": "kb1", "kb_origin": "KB1", "priority": 10,
                         "sources": [{"source_id": "P01", "type": "pdf", "title": "t", "publisher": "roadmap.sh",
                                      "trust": "medium"}]},
            "nodes": [{"label": "Skill", "key": "java", "name": "Java", "type": "technology", "aliases": ["java"],
                       "sources": ["P01"]},
                      {"label": "Skill", "key": "apache kafka", "name": "Apache Kafka", "type": "technology",
                       "sources": ["P01"]},
                      {"label": "Skill", "key": "kafka", "name": "Kafka", "type": "technology", "sources": ["P01"]},
                      {"label": "Category", "key": "relational databases", "name": "Relational Databases",
                       "sibling_ok_suggest": False}],
            "edges": [], "patches": [], "sha256": "0"}
    kb3 = kb3_pack(
        new_skills=["Spring Boot,technology,springboot,spring,Java Frameworks,java,Backend",
                    "Kafka Streams,technology,,,,apache kafka,Data"],
        skill_aliases=["java,lập trình java,"],
        skill_fixes=["same_as,apache kafka,kafka,trùng"],
        categories=["Java Frameworks,true,", "Relational Databases,true,"],
        titles=["Java Developer,lập trình viên java,,Backend"],
        near=["Fullstack,Backend,0.8,"],
    )
    assert validate_pack(kb3) == []
    r = run([base, kb3], ["Backend", "Fullstack", "Data"])
    assert r["errors"] == [] and r["review"] == []
    skills = {n["key"]: n for n in r["nodes"] if n["label"] == "Skill"}
    assert skills["spring boot"]["ambiguous_aliases"] == ["spring"]
    assert "lap trinh java" in skills["java"]["aliases"]
    parents = {(e["src"], e["dst"]) for e in r["edges"] if e["type"] == "PARENT_OF"}
    assert {("java", "spring boot"), ("kafka", "kafka streams")} <= parents
    cats = {n["key"]: n for n in r["nodes"] if n["label"] == "Category"}
    assert cats["relational databases"]["sibling_ok_suggest"] is True        # override của KB3
    ev = next(e for e in r["edges"] if e["type"] == "PARENT_OF")["evidence"][0]
    assert ev["page"] == 2 and ev["quote"].startswith("Spring Boot,")        # quote là nguyên dòng nguồn


def test_kb1_and_kb2_to_pack():
    nodes = [{"label": "Skill", "key": "docker", "name": "Docker", "type": "technology", "aliases": ["docker"],
              "ambiguous_aliases": []}]
    edges = [{"type": "EVIDENCED_BY", "src": "docker", "dst": "P10", "sources": ["P10"], "page": 1,
              "snippet": "Containers > Docker", "evidence": [{"source_id": "P10", "page": 1, "quote": "Containers > Docker"}]},
             {"type": "USED_IN", "src": "docker", "dst": "DevOps", "sources": ["P10"], "evidence": [],
              "in_roadmap": True, "node_kind": "sub"}]
    pack_nodes, pack_edges = kb1_to_pack(nodes, edges)
    assert pack_nodes[0]["sources"] == ["P10"] and pack_edges[1]["evidence"][0]["quote"] == "Containers > Docker"
    files = [[{"label": "JobTitle", "key": "ba", "name": "BA", "itviec_group": "G", "aliases": [],
               "ambiguous_aliases": []}, {"label": "Source", "source_id": "W01", "trust": "medium"}]]
    sources, n2, e2 = kb2_to_pack(files, [{"type": "MAPS_TO", "src": "ba", "dst": "Business", "sources": ["W01"],
                                          "evidence": [{"source_id": "W01", "page": 1, "quote": "q"}]}])
    assert sources == [{"source_id": "W01", "trust": "medium"}] and n2[0]["sources"] == ["W01"]
    assert "sources" not in e2[0]
