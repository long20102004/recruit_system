"""Gộp KB1 + KB2 thành một KB, ghi out/, rồi nạp vào Neo4j với nhãn Skill, Category, JobTitle, Level, Major,
Source.

Mỗi lần nạp thay toàn bộ các nhãn đó và quan hệ NEAR trong một giao dịch, để quan hệ cũ không còn sót lại.
KB tái tạo được từ kb1/out và kb2/out. RoleGroup được giữ. NEAR computed tính từ USED_IN của KB đã gộp.
Mọi nút và quan hệ vẫn là 'candidate'.

Chạy: python load_kb.py               gộp rồi nạp
      python load_kb.py --merge-only  chỉ gộp và kiểm tra, không đụng Neo4j
"""
import argparse
import collections
import itertools
import json
import os
import pathlib

from dotenv import load_dotenv
from neo4j import GraphDatabase

from shared.common import read_jsonl, write_jsonl
from shared.config import ROLE_GROUPS

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "out"
KB1_OUT, KB2_OUT = ROOT / "kb1" / "out", ROOT / "kb2" / "out"
# Tên KB -> (các file nút, các file quan hệ)
KB_FILES = {"KB1": ([KB1_OUT / "kb1_nodes.jsonl"], [KB1_OUT / "kb1_edges.jsonl"]),
            "KB2": ([KB2_OUT / "kb2_nodes.jsonl", KB2_OUT / "kb2_major_nodes.jsonl", KB2_OUT / "kb2_level_nodes.jsonl"],
                    [KB2_OUT / "kb2_edges.jsonl"])}

CONSTRAINTS = [("Skill", "key"), ("Category", "key"), ("JobTitle", "key"), ("Level", "key"), ("Major", "key"),
               ("Source", "source_id"), ("RoleGroup", "name")]
# Loại quan hệ -> (nhãn nút đầu, nhãn nút cuối); None là RoleGroup
EDGE_ENDS = {"IN_CATEGORY": ("Skill", "Category"), "PARENT_OF": ("Skill", "Skill"), "USED_IN": ("Skill", None),
             "EVIDENCED_BY": ("Skill", "Source"), "MAPS_TO": ("JobTitle", None), "NEAR": (None, None)}

COMMON_NODE_SET = "x.kb_origin = r.kb_origin, x.status = 'candidate', x.updated_at = datetime()"
NODE_QUERIES = {
    "Source": f"""UNWIND $rows AS r MERGE (x:Source {{source_id:r.source_id}}) SET x += r, {COMMON_NODE_SET}""",
    "Skill": f"""UNWIND $rows AS r MERGE (x:Skill {{key:r.key}})
                 SET x.name = r.name, x.type = r.type, x.aliases = r.aliases,
                     x.ambiguous_aliases = r.ambiguous_aliases, {COMMON_NODE_SET}""",
    "Category": f"""UNWIND $rows AS r MERGE (x:Category {{key:r.key}})
                    SET x.name = r.name, x.sibling_ok_suggest = r.sibling_ok_suggest, {COMMON_NODE_SET}""",
    "JobTitle": f"""UNWIND $rows AS r MERGE (x:JobTitle {{key:r.key}})
                    SET x.name = r.name, x.itviec_group = r.itviec_group, x.aliases = r.aliases,
                        x.ambiguous_aliases = r.ambiguous_aliases, {COMMON_NODE_SET}""",
    "Level": f"""UNWIND $rows AS r MERGE (x:Level {{key:r.key}})
                 SET x.name = r.name, x.rank = r.rank, x.aliases = r.aliases,
                     x.ambiguous_aliases = r.ambiguous_aliases, {COMMON_NODE_SET}""",
    "Major": f"""UNWIND $rows AS r MERGE (x:Major {{key:r.key}})
                 SET x.name = r.name, x.group = r.group, x.aliases = r.aliases,
                     x.ambiguous_aliases = r.ambiguous_aliases, {COMMON_NODE_SET}""",
}

COMMON_EDGE_SET = "e.sources = r.sources, e.evidence = r.evidence, e.status = 'candidate', e.updated_at = datetime()"
EDGE_QUERIES = {
    "IN_CATEGORY": f"""UNWIND $rows AS r MATCH (a:Skill {{key:r.src}}), (b:Category {{key:r.dst}})
                       MERGE (a)-[e:IN_CATEGORY]->(b) SET {COMMON_EDGE_SET}""",
    "PARENT_OF": f"""UNWIND $rows AS r MATCH (a:Skill {{key:r.src}}), (b:Skill {{key:r.dst}})
                     MERGE (a)-[e:PARENT_OF]->(b) SET {COMMON_EDGE_SET}""",
    "USED_IN": f"""UNWIND $rows AS r MATCH (a:Skill {{key:r.src}}), (g:RoleGroup {{name:r.dst}})
                   MERGE (a)-[e:USED_IN]->(g)
                   SET e.in_roadmap = r.in_roadmap, e.node_kind = r.node_kind, {COMMON_EDGE_SET}""",
    "EVIDENCED_BY": f"""UNWIND $rows AS r MATCH (a:Skill {{key:r.src}}), (s:Source {{source_id:r.dst}})
                        MERGE (a)-[e:EVIDENCED_BY]->(s)
                        SET e.page = r.page, e.snippet = r.snippet, e.kb = 'KB1', {COMMON_EDGE_SET}""",
    "MAPS_TO": f"""UNWIND $rows AS r MATCH (a:JobTitle {{key:r.src}}), (g:RoleGroup {{name:r.dst}})
                   MERGE (a)-[e:MAPS_TO]->(g) SET e.method = r.method, {COMMON_EDGE_SET}""",
    # method nằm trong khoá: một cặp nhóm có thể có cả computed và hypothesis để so sánh
    "NEAR": f"""UNWIND $rows AS r MATCH (a:RoleGroup {{name:r.src}}), (b:RoleGroup {{name:r.dst}})
                MERGE (a)-[e:NEAR {{method:r.method}}]->(b)
                SET e.m = r.m, e.shared_skills = r.shared_skills, {COMMON_EDGE_SET}""",
}


def node_id(node):
    return node.get("key") or node["source_id"]


def near_edges(edges):
    """NEAR computed: hệ số Jaccard trên kỹ năng USED_IN của hai nhóm. Lưu một chiều (Knowledge base.md, 2.4).

    Giá trị này đo độ trùng kỹ năng trong roadmap, không cùng thang với ma trận M của Rerank.
    """
    skills, sources = collections.defaultdict(set), collections.defaultdict(set)
    for edge in edges:
        if edge["type"] == "USED_IN":
            skills[edge["dst"]].add(edge["src"])
            sources[edge["dst"]].update(edge["sources"])
    pairs = [(a, b) for a, b in itertools.combinations(ROLE_GROUPS, 2) if skills[a] and skills[b]]
    return [{"type": "NEAR", "src": a, "dst": b, "method": "computed",
             "m": round(len(skills[a] & skills[b]) / len(skills[a] | skills[b]), 3),
             "shared_skills": len(skills[a] & skills[b]),
             "sources": sorted(sources[a] | sources[b]), "evidence": []} for a, b in pairs]


def merge_kb(kbs):
    """Hàm thuần. kbs: {tên KB: (nodes, edges)}. Trả (nodes, edges, checks).

    Hai KB cùng một nút hoặc quan hệ thì gộp alias, nguồn và bằng chứng, ghi kb_origin cả hai.
    """
    nodes, edges = {}, {}
    for origin, (kb_nodes, kb_edges) in kbs.items():
        for row in kb_nodes:
            merged = nodes.setdefault((row["label"], node_id(row)), {**row, "kb_origin": []})
            merged["kb_origin"].append(origin)
            for field in ("aliases", "ambiguous_aliases"):
                if field in row:
                    merged[field] = sorted({*merged[field], *row[field]})
        for row in kb_edges:
            merged = edges.setdefault((row["type"], row["src"], row["dst"]),
                                      {**row, "sources": [], "evidence": []})
            merged["sources"] += [s for s in row["sources"] if s not in merged["sources"]]
            merged["evidence"] += [p for p in row["evidence"] if p not in merged["evidence"]]
    kb_nodes, kb_edges = list(nodes.values()), list(edges.values())
    kb_edges += near_edges(kb_edges)
    return kb_nodes, kb_edges, make_checks(kb_nodes, kb_edges)


def make_checks(nodes, edges):
    """Các kiểm tra ở mục 10 của Knowledge base.md làm được khi chưa cấp status accepted."""
    ids = collections.defaultdict(set, {None: set(ROLE_GROUPS)})
    owners = collections.defaultdict(set)
    for node in nodes:
        ids[node["label"]].add(node_id(node))
        for alias in [*node.get("aliases", []), *node.get("ambiguous_aliases", [])]:
            owners[(node["label"], alias)].add(node_id(node))
    dangling = [[e["type"], e["src"], e["dst"]] for e in edges
                if e["src"] not in ids[EDGE_ENDS[e["type"]][0]] or e["dst"] not in ids[EDGE_ENDS[e["type"]][1]]]
    mapped = {e["src"] for e in edges if e["type"] == "MAPS_TO"}
    return {"nodes": dict(collections.Counter(n["label"] for n in nodes)),
            "edges": dict(collections.Counter(e["type"] for e in edges)),
            "alias_conflicts": {f"{label}: {alias}": sorted(keys) for (label, alias), keys in owners.items()
                                if len(keys) > 1},
            "dangling_edges": dangling,
            "job_titles_without_role_group": len(ids["JobTitle"] - mapped)}


def flatten_evidence(edge):
    """Neo4j chỉ lưu danh sách giá trị đơn, nên mỗi evidence thành một chuỗi JSON."""
    return {**edge, "evidence": [json.dumps(p, ensure_ascii=False) for p in edge["evidence"]]}


def write_all(tx, nodes, edges):
    """Một giao dịch: lỗi giữa chừng thì KB trong Neo4j giữ nguyên."""
    tx.run("""MATCH (n) WHERE n:Skill OR n:Category OR n:JobTitle OR n:Level OR n:Major OR n:Source
              DETACH DELETE n""").consume()
    tx.run("MATCH (:RoleGroup)-[r:NEAR]->(:RoleGroup) DELETE r").consume()
    tx.run("UNWIND $names AS g MERGE (:RoleGroup {name:g})", names=ROLE_GROUPS).consume()
    for label, query in NODE_QUERIES.items():
        tx.run(query, rows=[{k: v for k, v in n.items() if k != "label"}
                            for n in nodes if n["label"] == label]).consume()
    for kind, query in EDGE_QUERIES.items():
        tx.run(query, rows=[flatten_evidence(e) for e in edges if e["type"] == kind]).consume()


def load(nodes, edges):
    load_dotenv(ROOT / ".env")
    auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASS", "changeme123"))
    with GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=auth) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            for label, key in CONSTRAINTS:
                session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE").consume()
            session.execute_write(lambda tx: write_all(tx, nodes, edges))
            counts = session.run("""MATCH (n) WHERE n:Skill OR n:Category OR n:JobTitle OR n:Level OR n:Major
                                    OR n:Source OR n:RoleGroup RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label""").data()
            rels = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY type").data()
    print(f"Nút trong Neo4j: {counts}")
    print(f"Quan hệ trong Neo4j: {rels}")


def main():
    parser = argparse.ArgumentParser(description="Gộp KB1 + KB2 rồi nạp vào Neo4j")
    parser.add_argument("--merge-only", action="store_true", help="chỉ gộp và kiểm tra, không nạp")
    merge_only = parser.parse_args().merge_only

    kbs = {name: ([row for path in node_files for row in read_jsonl(path)],
                  [row for path in edge_files for row in read_jsonl(path)])
           for name, (node_files, edge_files) in KB_FILES.items()}
    if not all(nodes and edges for nodes, edges in kbs.values()):
        raise SystemExit("Một KB đang rỗng: không gộp để tránh xoá KB đang có")
    nodes, edges, checks = merge_kb(kbs)
    if checks["alias_conflicts"] or checks["dangling_edges"]:
        raise SystemExit(f"KB gộp có lỗi, không ghi: {json.dumps(checks, ensure_ascii=False, indent=2)}")

    write_jsonl(OUT / "kb_nodes.jsonl", nodes)
    write_jsonl(OUT / "kb_edges.jsonl", edges)
    (OUT / "kb_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"KB gộp: {checks['nodes']}, {checks['edges']}, "
          f"{checks['job_titles_without_role_group']} chức danh chưa có nhóm vai trò")
    if not merge_only:
        load(nodes, edges)


if __name__ == "__main__":
    main()
