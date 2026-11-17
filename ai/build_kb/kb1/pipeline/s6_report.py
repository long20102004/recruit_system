"""Bước 6: xuất số liệu cho báo cáo vào kb1/out/report/. Tính từ jsonl, không cần Neo4j đang chạy.

Độ chính xác chỉ tính khi có đáp án gán tay (gold_groups.csv, gold_labels.csv). Chưa điền thì ghi
"chưa có đáp án", không sinh con số.
"""
import collections
import itertools

import pandas as pd

from shared.common import norm, read_jsonl
from kb1.pipeline.config import OUT, ROLE_GROUPS

REPORT = OUT / "report"
NO_GOLD = "chưa có đáp án"
EXAMPLE_PARENTS = ["Popular Vector DBs (pick one)", "Relational Databases", "Ollama"]


def gold_rows(path, column):
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, dtype=str).fillna("")
    return frame[frame[column].str.strip() != ""]


def group_accuracy(groups):
    gold = gold_rows(OUT / "gold_groups.csv", "parent_expected")
    if gold.empty:
        return NO_GOLD, 0
    predicted = {(r["pdf"], norm(r["child"])): norm(r["parent"] or "") for r in groups}
    hits = sum(predicted.get((g.pdf, norm(g.child))) == norm(g.parent_expected)
               for g in gold.itertuples())
    return round(hits / len(gold), 3), len(gold)


def label_accuracy(labels):
    gold = gold_rows(OUT / "gold_labels.csv", "type_expected")
    if gold.empty:
        return NO_GOLD, 0
    predicted = {l["key"]: l["type"] for l in labels}
    hits = sum(predicted.get(norm(g.label)) == g.type_expected.strip() for g in gold.itertuples())
    return round(hits / len(gold), 3), len(gold)


def write_stats(nodes, kb_nodes, edges):
    sources = {n["source_id"]: n["uri"].rsplit("/", 1)[-1].removesuffix(".pdf")
               for n in kb_nodes if n["label"] == "Source"}
    skills = collections.Counter(sources[e["dst"]] for e in edges if e["type"] == "EVIDENCED_BY")
    categories = collections.defaultdict(set)
    for e in edges:
        if e["type"] == "IN_CATEGORY":
            for source_id in e["sources"]:
                categories[sources[source_id]].add(e["dst"])
    rows = []
    for pdf in sorted({n["pdf"] for n in nodes}):
        kinds = collections.Counter(n["kind"] for n in nodes if n["pdf"] == pdf)
        rows.append({"pdf": pdf, "so_o": kinds["main"] + kinds["sub"], "o_chinh": kinds["main"],
                     "o_con": kinds["sub"], "tieu_de_nhom": kinds["heading"],
                     "nhan_loc_nhieu": kinds["noise"] + kinds["link"],
                     "so_ky_nang": skills[pdf], "so_nhom": len(categories[pdf])})
    pd.DataFrame(rows).to_csv(REPORT / "stats_per_pdf.csv", index=False, encoding="utf-8-sig")


def write_accuracy(groups, labels):
    group_score, group_n = group_accuracy(groups)
    label_score, label_n = label_accuracy(labels)
    methods = collections.Counter(l["method"] for l in labels)
    placed = collections.Counter(r["method"] for r in groups if r["child_kind"] == "sub")
    rows = [{"chi_so": "do_chinh_xac_gan_nhom", "gia_tri": group_score, "so_mau": group_n},
            {"chi_so": "do_chinh_xac_phan_loai_nhan", "gia_tri": label_score, "so_mau": label_n}]
    rows += [{"chi_so": f"ti_le_nhan_{k}", "gia_tri": round(v / len(labels), 3), "so_mau": v}
             for k, v in sorted(methods.items())]
    total = sum(placed.values())
    rows += [{"chi_so": f"ti_le_gan_cha_{k}", "gia_tri": round(v / total, 3), "so_mau": v}
             for k, v in sorted(placed.items())]
    pd.DataFrame(rows).to_csv(REPORT / "accuracy.csv", index=False, encoding="utf-8-sig")


def write_top_skills(kb_nodes, edges):
    name = {n["key"]: n["name"] for n in kb_nodes if n["label"] == "Skill"}
    counts = collections.Counter(e["src"] for e in edges if e["type"] == "EVIDENCED_BY")
    rows = [{"ky_nang": name[k], "so_roadmap": v} for k, v in counts.most_common(20)]
    pd.DataFrame(rows, columns=["ky_nang", "so_roadmap"]).to_csv(
        REPORT / "top_skills.csv", index=False, encoding="utf-8-sig")


def write_role_matrix(edges):
    skills = {g: set() for g in ROLE_GROUPS}
    for e in edges:
        if e["type"] == "USED_IN":
            skills[e["dst"]].add(e["src"])
    rows = [{"nhom_a": g, "nhom_b": g, "so_ky_nang_chung": len(skills[g]), "jaccard": 1.0}
            for g in ROLE_GROUPS]
    for a, b in itertools.combinations(ROLE_GROUPS, 2):
        union = skills[a] | skills[b]
        rows.append({"nhom_a": a, "nhom_b": b, "so_ky_nang_chung": len(skills[a] & skills[b]),
                     "jaccard": round(len(skills[a] & skills[b]) / len(union), 3) if union else 0.0})
    pd.DataFrame(rows).to_csv(REPORT / "role_skill_matrix.csv", index=False, encoding="utf-8-sig")


def write_examples(groups, kb_nodes, edges):
    lines = ["# Ví dụ IN–OUT", ""]
    for parent in EXAMPLE_PARENTS:
        rows = [r for r in groups if r["parent"] == parent and r["child_kind"] == "sub"]
        if not rows:
            continue
        key = norm(parent)
        related = [e for e in edges if key in (e["src"], e["dst"])
                   and e["type"] in ("IN_CATEGORY", "PARENT_OF")]
        category = next((n for n in kb_nodes if n["label"] == "Category" and n["key"] == key), None)
        lines += [f"## {parent} ({rows[0]['pdf']})", "", "**IN (ô trên sơ đồ):** "
                  + ", ".join(sorted({r["child"] for r in rows})), "", "**OUT:**", ""]
        if category:
            lines.append(f"- `KB1_Category` \"{category['name']}\", "
                         f"`sibling_ok_suggest = {str(category['sibling_ok_suggest']).lower()}`")
        lines += [f"- `{e['src']}` -[{e['type']}]-> `{e['dst']}`" for e in related]
        if not category and not related:
            lines.append("- chưa sinh quan hệ nào (nhãn chưa được phân loại)")
        lines.append("")
    (REPORT / "examples.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    nodes = read_jsonl(OUT / "nodes_grouped.jsonl")
    groups = read_jsonl(OUT / "groups.jsonl")
    labels = read_jsonl(OUT / "labels.jsonl")
    kb_nodes = read_jsonl(OUT / "kb1_nodes.jsonl")
    edges = read_jsonl(OUT / "kb1_edges.jsonl")

    write_stats(nodes, kb_nodes, edges)
    write_accuracy(groups, labels)
    write_top_skills(kb_nodes, edges)
    write_role_matrix(edges)
    write_examples(groups, kb_nodes, edges)
    print(f"Đã ghi báo cáo vào {REPORT}")


if __name__ == "__main__":
    main()
