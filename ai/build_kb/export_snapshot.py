"""Xuất bản chụp KB cho module match (thiết kế 02 mục 8, kế hoạch T01).

Đọc KB trong Neo4j, cấp `skill_id` ổn định, kiểm tra (mục 10), rồi ghi thư mục
`out/snapshot/<ontology_version>/` gồm 5 file JSONL + manifest.json. Module `cvmatch` nạp thư mục
này bằng `cvmatch kb import` (không đọc Neo4j lúc chạy).

- `skill_id` (S0001...) lưu ở `out/skill_ids.csv` (key -> skill_id), vì `load_kb.py` xoá và tạo lại
  nút Skill mỗi lần nạp. Key đã có giữ nguyên mã; key mới cấp tiếp số lớn nhất; mã đã dùng không cấp lại.
- Q-3 (đã chốt 14/11/2026): tạm thời xuất CẢ `candidate` (mặc định). `--accepted-only` khi KB đã duyệt.
  Bản có candidate mang hậu tố `-dev` và cột `status` cho từng kỹ năng.
- `sibling_ok`: dùng thuộc tính `sibling_ok` nếu người duyệt đã đặt (hoặc kb_pipeline policy provisional đã nhận
  tạm từ `sibling_ok_suggest`, `sibling_ok_by = provisional`); bản dev dùng tạm `sibling_ok_suggest`.
- Alias dễ nhầm: `ambiguous_aliases` của KB + mọi alias ≤ 2 ký tự không có ký tự đặc biệt
  ("if", "ip", "js", "s3"...) - không tự khớp trong văn bản tự do, chỉ khớp khi là nguyên phần tử
  của mảng kỹ năng.
- Alias chuẩn hoá: NFC, chữ thường, gộp khoảng trắng (cvmatch chuẩn hoá lại bằng đúng hàm A4 khi nạp).

Chạy:  python export_snapshot.py                  xuất bản dev (cả candidate)
       python export_snapshot.py --accepted-only  chỉ tri thức đã duyệt
       python export_snapshot.py --dry-run        chỉ kiểm tra, không ghi
       python export_snapshot.py --from-out       đọc out/kb_nodes.jsonl, out/kb_edges.jsonl thay vì Neo4j
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re

from kb_pipeline.quality import find_cycle
from shared.common import norm
from shared.config import ROLE_GROUPS

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "out"
SKILL_IDS = OUT / "skill_ids.csv"
FILES = ("skill_ontology", "role_title_map", "role_distance", "major_group", "ambiguous_aliases")

_SPECIAL = re.compile(r"[#+./\-]")


# --------------------------------------------------------------------------- đọc Neo4j

def read_neo4j():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(ROOT / ".env")
    auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASS", "changeme123"))
    q = {
        "skills": """MATCH (n:Skill) OPTIONAL MATCH (n)-[:EVIDENCED_BY]->(s:Source)
                     RETURN n.key AS key, n.name AS name, n.type AS type, n.aliases AS aliases,
                            n.ambiguous_aliases AS ambiguous_aliases, n.status AS status, count(s) AS n_evidence""",
        "parent_of": """MATCH (a:Skill)-[r:PARENT_OF]->(b:Skill)
                        RETURN a.key AS parent, b.key AS child, r.status AS status""",
        "in_category": """MATCH (a:Skill)-[r:IN_CATEGORY]->(c:Category)
                          RETURN a.key AS skill, c.key AS category, r.status AS status,
                                 c.sibling_ok AS sibling_ok, c.sibling_ok_suggest AS sibling_ok_suggest,
                                 c.status AS category_status""",
        "titles": """MATCH (t:JobTitle) OPTIONAL MATCH (t)-[r:MAPS_TO]->(g:RoleGroup)
                     RETURN t.key AS key, t.name AS name, t.aliases AS aliases, t.status AS status,
                            collect(CASE WHEN g IS NULL THEN NULL ELSE {group: g.name, status: r.status} END) AS groups""",
        "levels": "MATCH (n:Level) RETURN n.key AS key, n.name AS name, n.rank AS rank, n.aliases AS aliases, n.status AS status",
        "majors": "MATCH (n:Major) RETURN n.key AS key, n.name AS name, n.group AS group, n.aliases AS aliases, n.status AS status",
        "near": """MATCH (a:RoleGroup)-[r:NEAR]->(b:RoleGroup)
                   RETURN a.name AS a, b.name AS b, r.m AS m, r.method AS method, r.status AS status""",
    }
    with GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"), auth=auth) as driver:
        driver.verify_connectivity()
        with driver.session() as s:
            return {k: s.run(v).data() for k, v in q.items()}


def read_out(out=OUT):
    """Cùng dạng dữ liệu với read_neo4j(), đọc từ KB do kb_pipeline ghi (không cần Neo4j)."""
    def jl(name):
        with open(out / name, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    nodes, edges = jl("kb_nodes.jsonl"), jl("kb_edges.jsonl")
    of = collections.defaultdict(dict)
    for n in nodes:
        of[n["label"]][n.get("key") or n.get("source_id")] = n
    n_ev = collections.Counter(e["src"] for e in edges if e["type"] == "EVIDENCED_BY")
    groups = collections.defaultdict(list)
    for e in edges:
        if e["type"] == "MAPS_TO":
            groups[e["src"]].append({"group": e["dst"], "status": e["status"]})

    def base(n, *fields):
        return {"key": n["key"], "name": n["name"], "aliases": n.get("aliases") or [], "status": n["status"],
                **{f: n.get(f) for f in fields}}

    cats = of["Category"]
    return {
        "skills": [{**base(n, "type", "ambiguous_aliases"), "n_evidence": n_ev[k]} for k, n in of["Skill"].items()],
        "parent_of": [{"parent": e["src"], "child": e["dst"], "status": e["status"]}
                      for e in edges if e["type"] == "PARENT_OF"],
        "in_category": [{"skill": e["src"], "category": e["dst"], "status": e["status"],
                         "sibling_ok": cats.get(e["dst"], {}).get("sibling_ok"),
                         "sibling_ok_suggest": cats.get(e["dst"], {}).get("sibling_ok_suggest"),
                         "category_status": cats.get(e["dst"], {}).get("status")}
                        for e in edges if e["type"] == "IN_CATEGORY"],
        "titles": [{**base(n), "groups": groups[k]} for k, n in of["JobTitle"].items()],
        "levels": [base(n, "rank") for n in of["Level"].values()],
        "majors": [base(n, "group") for n in of["Major"].values()],
        "near": [{"a": e["src"], "b": e["dst"], "m": e.get("m"), "method": e.get("method"), "status": e["status"]}
                 for e in edges if e["type"] == "NEAR"],
    }


# --------------------------------------------------------------------------- skill_id

def load_skill_ids(path=SKILL_IDS):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {r["key"]: r["skill_id"] for r in csv.DictReader(f)}


def assign_skill_ids(keys, existing):
    """Giữ mã cũ; key mới (sắp theo tên) cấp tiếp từ số lớn nhất từng dùng. Trả về dict đầy đủ."""
    ids = dict(existing)
    used = [int(v[1:]) for v in ids.values() if re.fullmatch(r"S\d+", v)]
    nxt = max(used, default=0) + 1
    for k in sorted(set(keys) - set(ids)):
        ids[k] = f"S{nxt:04d}"
        nxt += 1
    return ids


def save_skill_ids(ids, path=SKILL_IDS):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "skill_id"])
        for k, v in sorted(ids.items(), key=lambda x: x[1]):
            w.writerow([k, v])


# --------------------------------------------------------------------------- dựng snapshot (hàm thuần)

def _ok(status, include_candidate):
    return status == "accepted" or (include_candidate and status in (None, "candidate"))


def build_snapshot(data, skill_ids, *, include_candidate=True):
    """data: kết quả read_neo4j(). Trả (rows {file: [dòng]}, report {kiểm tra + thống kê})."""
    skills = [s for s in data["skills"] if _ok(s["status"], include_candidate)]
    key_to_id = {s["key"]: skill_ids[s["key"]] for s in skills}

    # --- alias, alias dễ nhầm
    owners = collections.defaultdict(set)              # alias -> skill_id (alias tự do)
    amb = collections.defaultdict(set)                 # alias dễ nhầm -> skill_id
    for s in skills:
        sid = key_to_id[s["key"]]
        ambiguous = {norm(x) for x in s.get("ambiguous_aliases") or []}
        # tên trùng từ thường ("cat", "head") đã bị KB3 chuyển sang ambiguous: không thành alias tự do nữa
        for a in {norm(s["name"]), *(norm(x) for x in s.get("aliases") or [])} - ambiguous:
            if a:
                owners[a].add(sid)
        for a in ambiguous:
            if a:
                amb[a].add(sid)
    for a, sids in list(owners.items()):
        if len(a) <= 2 and not _SPECIAL.search(a):
            amb[a] |= sids
    conflicts = {a: sorted(v) for a, v in owners.items() if len(v) > 1}

    parents = collections.defaultdict(list)
    parent_edges = []
    for e in data["parent_of"]:
        if _ok(e["status"], include_candidate) and e["parent"] in key_to_id and e["child"] in key_to_id:
            parents[key_to_id[e["child"]]].append(key_to_id[e["parent"]])
            parent_edges.append((key_to_id[e["parent"]], key_to_id[e["child"]]))
    sib = collections.defaultdict(list)
    for e in data["in_category"]:
        if e["skill"] not in key_to_id or not _ok(e["status"], include_candidate):
            continue
        flag = e["sibling_ok"] if e["sibling_ok"] is not None else (
            e["sibling_ok_suggest"] if include_candidate else False)
        if flag and _ok(e["category_status"], include_candidate):
            sib[key_to_id[e["skill"]]].append(e["category"])

    skill_rows = []
    for s in sorted(skills, key=lambda s: key_to_id[s["key"]]):
        sid = key_to_id[s["key"]]
        aliases = sorted(a for a, v in owners.items() if sid in v and len(v) == 1)
        # alias dễ nhầm chỉ thuộc một kỹ năng: vẫn là alias (để khớp nguyên phần tử mảng skills)
        aliases += sorted(a for a, v in amb.items() if v == {sid} and a not in aliases)
        skill_rows.append({"skill_id": sid, "name": s["name"], "aliases": aliases, "type": s["type"],
                           "parents": sorted(set(parents[sid])),
                           "categories_sibling_ok": sorted(set(sib[sid])),
                           "status": s["status"] or "candidate"})
    amb_rows = [{"alias": a, "candidates": sorted(v)} for a, v in sorted(amb.items())]

    # --- chức danh -> nhóm vai trò; cấp bậc
    title_rows, multi_group, no_group, seen = [], [], 0, {}
    order = {g: i for i, g in enumerate(ROLE_GROUPS)}
    for t in data["titles"]:
        if not _ok(t["status"], include_candidate):
            continue
        groups = sorted({g["group"] for g in t["groups"] if g and _ok(g["status"], include_candidate)},
                        key=lambda g: order.get(g, 99))
        if not groups:
            no_group += 1
            continue
        if len(groups) > 1:
            multi_group.append({"title": t["name"], "groups": groups, "chosen": groups[0]})
        for a in {norm(t["name"]), *(norm(x) for x in t.get("aliases") or [])}:
            if a and a not in seen:
                seen[a] = groups[0]
                title_rows.append({"kind": "title", "alias": a, "role_group": groups[0]})
    for lv in data["levels"]:
        if _ok(lv["status"], include_candidate):
            for a in sorted({norm(lv["name"]), *(norm(x) for x in lv.get("aliases") or [])}):
                title_rows.append({"kind": "level", "alias": a, "level_rank": int(lv["rank"])})

    major_rows, seen_major = [], set()
    for mj in data["majors"]:
        if _ok(mj["status"], include_candidate):
            for a in sorted({norm(mj["name"]), *(norm(x) for x in mj.get("aliases") or [])}):
                if a not in seen_major:
                    seen_major.add(a)
                    major_rows.append({"major_alias": a, "group": mj["group"]})

    # NEAR hypothesis (ma trận M giả thuyết của thiết kế 07 mục 5.6, nằm trong gói kb3-generated) và computed
    dist_rows = [{"group_a": e["a"], "group_b": e["b"], "m": float(e["m"]), "method": e["method"]}
                 for e in data["near"] if e.get("method") in ("hypothesis", "computed")
                 and _ok(e["status"], include_candidate)]

    rows = {"skill_ontology": skill_rows, "role_title_map": title_rows, "role_distance": dist_rows,
            "major_group": major_rows, "ambiguous_aliases": amb_rows}
    report = {
        "blocking": {"alias_conflicts": conflicts, "parent_cycles": [c] if (c := find_cycle(parent_edges)) else []},
        "warnings": {
            "skills_without_evidence": sum(1 for s in skills if not s.get("n_evidence")),
            "job_titles_without_role_group": no_group,
            "job_titles_multi_group": multi_group,
        },
        "stats": {
            "n_skills": len(skill_rows), "n_technology": sum(r["type"] == "technology" for r in skill_rows),
            "n_aliases": sum(len(r["aliases"]) for r in skill_rows), "n_ambiguous_aliases": len(amb_rows),
            "n_parent_of": len(parent_edges), "n_skills_with_sibling_category": sum(bool(r["categories_sibling_ok"]) for r in skill_rows),
            "n_title_aliases": sum(r["kind"] == "title" for r in title_rows),
            "n_level_aliases": sum(r["kind"] == "level" for r in title_rows),
            "n_major_aliases": len(major_rows), "role_groups": sorted({r["role_group"] for r in title_rows if r["kind"] == "title"}),
        },
    }
    return rows, report


# --------------------------------------------------------------------------- ghi

def write_snapshot(rows, report, version, include_candidate, out_root=OUT / "snapshot", source="neo4j"):
    d = out_root / version
    d.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in FILES:
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows[name])
        (d / f"{name}.jsonl").write_text(text, encoding="utf-8")
        files[name] = {"rows": len(rows[name]), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    manifest = {"ontology_version": version, "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "include_candidate": include_candidate, "source": source, "files": files,
                "stats": report["stats"], "warnings": report["warnings"]}
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return d


def main():
    ap = argparse.ArgumentParser(description="Xuất bản chụp KB cho module match")
    ap.add_argument("--accepted-only", action="store_true", help="chỉ xuất status = accepted")
    ap.add_argument("--version", default=None, help="mặc định kb-YYYY-MM-DD (+ -dev nếu có candidate)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-out", action="store_true", help="đọc KB từ out/*.jsonl (không cần Neo4j)")
    args = ap.parse_args()
    include_candidate = not args.accepted_only
    # ontology_version = KBVersion.id (thiết kế mục 8): phiên bản cuối do kb_pipeline ghi ở out/versions.jsonl
    versions = OUT / "versions.jsonl"
    lines = versions.read_text(encoding="utf-8").splitlines() if versions.exists() else []
    base = json.loads(lines[-1])["id"] if lines else f"kb-{dt.date.today().isoformat()}"
    version = args.version or base + ("-dev" if include_candidate else "")

    data = read_out() if args.from_out else read_neo4j()
    ids = assign_skill_ids([s["key"] for s in data["skills"]], load_skill_ids())
    rows, report = build_snapshot(data, ids, include_candidate=include_candidate)
    print(json.dumps({"stats": report["stats"], "warnings": report["warnings"]}, ensure_ascii=False, indent=2))
    if any(report["blocking"].values()):
        raise SystemExit(f"KB có lỗi chặn, không xuất: {json.dumps(report['blocking'], ensure_ascii=False, indent=2)}")
    if args.dry_run:
        return
    save_skill_ids(ids)
    source = "out/kb_*.jsonl" if args.from_out else "neo4j"
    print(f"Đã xuất: {write_snapshot(rows, report, version, include_candidate, source=source)}")


if __name__ == "__main__":
    main()
