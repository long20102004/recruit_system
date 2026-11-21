"""KB3: đóng gói các bảng tự sinh ở kb3/data/ thành gói đóng góp packs/kb3-generated/.

KB3 do AI (Claude) soạn để lấp chỗ trống của KB1 (roadmap PDF) và KB2 (ITviec): framework và công cụ còn thiếu,
alias tiếng Việt, PARENT_OF, sibling_ok, chức danh chưa có nhóm vai trò, ngành học, ma trận NEAR giả thuyết.
Mọi nguồn có type = generated, trust = low: theo Knowledge base.md mục 6 KB3 không tự đủ để thành accepted.

Adapter này không đọc KB1/KB2: thực thể và đầu mút quan hệ gọi theo tên, thư ký chung (kb_pipeline) tự đối chiếu,
tự bỏ alias đã thuộc nút khác và ghi vào hàng đợi duyệt. Bảng sửa KB đã có (gộp trùng, loại nhãn rác...) thành
patches.jsonl. Bằng chứng là {source_id, page = số dòng trong file, quote = nguyên dòng đó}.

Chạy: python -m kb3.pipeline.build
"""
import csv
import hashlib

from kb3.pipeline.config import DATA, FILES, SOURCES_CSV
from kb_pipeline.packs import write_pack

PACK_ID, PRIORITY = "kb3-generated", 30


def read_table(name):
    """Trả [(số dòng, dòng gốc, dict)]. Dòng tiêu đề là dòng 1; dữ liệu không có ô nhiều dòng."""
    lines = (DATA / FILES[name][0]).read_text(encoding="utf-8").splitlines()
    rows = list(csv.DictReader(lines))
    return [(i + 2, lines[i + 1], row) for i, row in enumerate(rows)]


def split(cell):
    return [x.strip() for x in (cell or "").split("|") if x.strip()]


def proof(name, line_no, line):
    return {"source_id": FILES[name][1], "page": line_no, "quote": line}


def build(tables):
    """Hàm thuần: bảng -> (nodes, edges, patches) theo định dạng gói."""
    nodes, edges, patches = [], [], []

    def edge(kind, src, dst, ev, **props):
        edges.append({"type": kind, "src": src, "dst": dst, "evidence": [ev], **props})

    for line_no, line, r in tables["skill_fixes"]:
        ev = proof("skill_fixes", line_no, line)
        op, key, value = r["op"], r["key"], r["value"]
        if op == "same_as":
            patches.append({"op": "same_as", "label": "Skill", "drop": key, "keep": value, "evidence": ev})
        elif op in ("reject", "ambiguous"):
            patches.append({"op": op, "label": "Skill", "ref": key, "evidence": ev})
        elif op == "type":
            patches.append({"op": "set", "label": "Skill", "ref": key, "fields": {"type": value}, "evidence": ev})
        elif op == "drop_category":
            patches.append({"op": "drop_edge", "type": "IN_CATEGORY", "src": key, "dst": value, "evidence": ev})
        else:
            patches.append({"op": op, "evidence": ev})              # validate_pack báo op sai

    # sibling_ok của KB3 là ý định sửa, nên thắng giá trị của gói trước (override)
    for line_no, line, r in tables["categories"]:
        nodes.append({"label": "Category", "name": r["name"], "sibling_ok_suggest": r["sibling_ok"].lower() == "true",
                      "override": ["sibling_ok_suggest"], "sources": [FILES["categories"][1]]})

    for line_no, line, r in tables["new_skills"]:
        ev = proof("new_skills", line_no, line)
        nodes.append({"label": "Skill", "name": r["name"], "type": r["type"], "aliases": split(r["aliases"]),
                      "ambiguous_aliases": split(r["ambiguous_aliases"]), "sources": [ev["source_id"]]})
        edge("EVIDENCED_BY", r["name"], ev["source_id"], ev, page=line_no, snippet=line)
        for cat in split(r["categories"]):
            edge("IN_CATEGORY", r["name"], cat, ev)
        for parent in split(r["parents"]):
            edge("PARENT_OF", parent, r["name"], ev)
        for group in split(r["role_groups"]):
            edge("USED_IN", r["name"], group, ev, in_roadmap=False)

    for line_no, line, r in tables["skill_aliases"]:
        nodes.append({"label": "Skill", "ref": r["key"], "aliases": split(r["aliases"]),
                      "ambiguous_aliases": split(r["ambiguous_aliases"]), "sources": [FILES["skill_aliases"][1]]})

    for line_no, line, r in tables["edges"]:
        props = {"in_roadmap": False} if r["type"] == "USED_IN" else {}
        edge(r["type"], r["src"], r["dst"], proof("edges", line_no, line), **props)

    for line_no, line, r in tables["titles"]:
        ev = proof("titles", line_no, line)
        nodes.append({"label": "JobTitle", "name": r["name"], "aliases": split(r["aliases"]),
                      "ambiguous_aliases": split(r["ambiguous_aliases"]), "sources": [ev["source_id"]]})
        for group in split(r["role_groups"]):
            edge("MAPS_TO", r["name"], group, ev, method="generated")

    for line_no, line, r in tables["levels"]:
        nodes.append({"label": "Level", "ref": r["name"], "aliases": split(r["aliases"]),
                      "ambiguous_aliases": split(r["ambiguous_aliases"]), "sources": [FILES["levels"][1]]})

    for line_no, line, r in tables["majors"]:
        nodes.append({"label": "Major", "name": r["name_en"], "group": r["group"],
                      "aliases": [r["name_vi"], *split(r["aliases"])], "sources": [FILES["majors"][1]]})

    for line_no, line, r in tables["near"]:
        edge("NEAR", r["group_a"], r["group_b"], proof("near", line_no, line), method="hypothesis", m=float(r["m"]))
    return nodes, edges, patches


def load_sources():
    with open(SOURCES_CSV, encoding="utf-8", newline="") as f:
        sources = list(csv.DictReader(f))
    by_id = {s["source_id"]: s for s in sources}
    for file_name, source_id in FILES.values():
        if source_id not in by_id:
            raise SystemExit(f"sources.csv chưa có {source_id}")
        by_id[source_id]["sha256"] = hashlib.sha256((DATA / file_name).read_bytes()).hexdigest()
    return sources


def main():
    nodes, edges, patches = build({name: read_table(name) for name in FILES})
    d = write_pack(PACK_ID, "KB3", PRIORITY, load_sources(), nodes, edges, patches,
                   description="KB3: tri thức do Claude sinh (trust = low) để lấp chỗ trống của KB1, KB2")
    print(f"Đã ghi gói {d}: {len(nodes)} khẳng định thực thể, {len(edges)} quan hệ, {len(patches)} bản vá")


if __name__ == "__main__":
    main()
