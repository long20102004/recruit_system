"""Thư ký chung, phần 4: ghi KB ra Neo4j và ra script Cypher (cùng một bộ câu lệnh).

Câu lệnh chung cho mọi nhãn và loại quan hệ: thuộc tính nút/quan hệ nằm phẳng trong r.props, nên thêm trường mới ở
schema không phải sửa câu lệnh. Mỗi lần nạp thay toàn bộ KB (trừ RoleGroup và KBVersion) trong một giao dịch.
"""
import json
import os

from kb_pipeline.schema import EDGE_ENDS, NODE_LABELS

KEY_OF = {**{label: "key" for label in NODE_LABELS}, "Source": "source_id", "RoleGroup": "name"}
KB_LABELS = (*NODE_LABELS, "Source")
CONSTRAINTS = [(label, KEY_OF[label]) for label in (*KB_LABELS, "RoleGroup")] + [("KBVersion", "id")]
CYPHER_BATCH = 200
DELETE_KB = ("MATCH (n) WHERE " + " OR ".join(f"n:{label}" for label in KB_LABELS) + " DETACH DELETE n")
DELETE_NEAR = "MATCH (:RoleGroup)-[r:NEAR]->(:RoleGroup) DELETE r"


def node_query(label):
    key = KEY_OF[label]
    return (f"UNWIND $rows AS r MERGE (x:{label} {{{key}: r.{key}}}) "
            f"SET x += r.props, x.updated_at = datetime()")


def edge_query(kind):
    a, b = EDGE_ENDS[kind]
    merge = "MERGE (a)-[e:NEAR {method: r.props.method}]->(b)" if kind == "NEAR" else f"MERGE (a)-[e:{kind}]->(b)"
    return (f"UNWIND $rows AS r MATCH (a:{a} {{{KEY_OF[a]}: r.src}}), (b:{b} {{{KEY_OF[b]}: r.dst}}) "
            f"{merge} SET e += r.props, e.updated_at = datetime()")


VERSION_QUERY = "UNWIND $rows AS r MERGE (v:KBVersion {id: r.id}) SET v += r.props"


def node_rows(nodes, label):
    key = KEY_OF[label]
    return [{key: n[key], "props": {k: v for k, v in n.items() if k != "label" and v is not None}}
            for n in nodes if n["label"] == label]


def edge_rows(edges, kind):
    """Neo4j không lưu map trong danh sách, nên mỗi evidence thành một chuỗi JSON."""
    rows = []
    for e in edges:
        if e["type"] != kind:
            continue
        props = {k: v for k, v in e.items() if k not in ("type", "src", "dst") and v is not None}
        props["evidence"] = [json.dumps(p, ensure_ascii=False) for p in e["evidence"]]
        rows.append({"src": e["src"], "dst": e["dst"], "props": props})
    return rows


def version_rows(version):
    return [{"id": version["id"], "props": {k: v for k, v in version.items() if v is not None}}]


def statements(nodes, edges, version, role_groups):
    """(câu lệnh, rows) theo thứ tự nạp. rows = None: câu lệnh không tham số."""
    out = [(DELETE_KB, None), (DELETE_NEAR, None),
           ("UNWIND $rows AS g MERGE (:RoleGroup {name: g})", list(role_groups))]
    out += [(node_query(label), node_rows(nodes, label)) for label in KB_LABELS]
    out += [(edge_query(kind), edge_rows(edges, kind)) for kind in EDGE_ENDS]
    out.append((VERSION_QUERY, version_rows(version)))
    return out


# --------------------------------------------------------------------------- Cypher

def cypher_value(value):
    """Giá trị Python -> literal Cypher. Chuỗi để trong nháy đơn, thoát dấu \\ và '."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        text = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
        return f"'{text}'"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(cypher_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"`{k}`: {cypher_value(v)}" for k, v in value.items()) + "}"
    raise TypeError(f"không đổi được sang Cypher: {type(value)}")


def to_cypher(nodes, edges, version, role_groups, summary):
    """Script dựng lại toàn bộ KB, mỗi lệnh một dòng kết thúc ';'. Chạy: cypher-shell -f out/kb.cypher."""
    lines = [f"// KB kỹ năng IT, phiên bản {version['id']}, sinh bởi kb_pipeline. Không sửa tay: sửa gói rồi chạy lại.",
             f"// {json.dumps(summary, ensure_ascii=False)}",
             "// Chạy: cypher-shell -u neo4j -p <mật khẩu> -f out/kb.cypher", ""]
    lines += [f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE;" for label, key in CONSTRAINTS]
    for query, rows in statements(nodes, edges, version, role_groups):
        if rows is None:
            lines.append(query + ";")
            continue
        body = query.replace("UNWIND $rows AS ", "", 1)
        var, rest = body.split(" ", 1)
        for i in range(0, len(rows), CYPHER_BATCH):
            lines.append(f"UNWIND {cypher_value(rows[i:i + CYPHER_BATCH])} AS {var} {rest};")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- Neo4j

def load_neo4j(nodes, edges, version, role_groups, env_file):
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(env_file)
    auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASS", "changeme123"))
    with GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=auth) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            for label, key in CONSTRAINTS:
                session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE").consume()

            def write(tx):
                for query, rows in statements(nodes, edges, version, role_groups):
                    tx.run(query, rows=rows).consume() if rows is not None else tx.run(query).consume()

            session.execute_write(write)
            counts = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label").data()
            rels = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY type").data()
    return counts, rels
