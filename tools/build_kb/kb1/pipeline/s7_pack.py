"""Bước 7: đóng gói KB1 thành gói đóng góp packs/kb1-roadmap/ cho thư ký chung (kb_pipeline).

Chỉ đổi định dạng, không thêm tri thức: đọc kb1/out/kb1_nodes.jsonl, kb1_edges.jsonl và kb1/data/sources.csv.
USED_IN của s5 không mang evidence, nên lấy evidence từ EVIDENCED_BY cùng kỹ năng, cùng nguồn.
Chạy sau s5_triples: python -m kb1.pipeline.s7_pack
"""
import collections

from kb1.pipeline.config import OUT
from kb1.pipeline.s5_triples import load_sources
from kb_pipeline.packs import write_pack
from shared.common import read_jsonl

PACK_ID, PRIORITY = "kb1-roadmap", 10


def to_pack(nodes, edges):
    """Hàm thuần: (nodes, edges) của KB1 -> (nodes, edges) theo định dạng gói."""
    by_skill = collections.defaultdict(list)                 # skill -> evidence của EVIDENCED_BY
    for e in edges:
        if e["type"] == "EVIDENCED_BY":
            by_skill[e["src"]] += e["evidence"]
    cat_sources = collections.defaultdict(set)
    for e in edges:
        if e["type"] == "IN_CATEGORY":
            cat_sources[e["dst"]] |= set(e["sources"])

    pack_nodes = []
    for n in nodes:
        if n["label"] == "Skill":
            pack_nodes.append({**n, "sources": sorted({p["source_id"] for p in by_skill[n["key"]]})})
        elif n["label"] == "Category":
            pack_nodes.append({**n, "sources": sorted(cat_sources[n["key"]])})
    pack_edges = []
    for e in edges:
        row = {k: v for k, v in e.items() if k != "sources"}
        if not row["evidence"]:
            row["evidence"] = [p for p in by_skill[e["src"]] if p["source_id"] in e["sources"]]
        pack_edges.append(row)
    return pack_nodes, pack_edges


def main():
    nodes, edges = to_pack(read_jsonl(OUT / "kb1_nodes.jsonl"), read_jsonl(OUT / "kb1_edges.jsonl"))
    d = write_pack(PACK_ID, "KB1", PRIORITY, load_sources(), nodes, edges,
                   description="KB1: 18 roadmap PDF của roadmap.sh, alias từ tag synonyms Stack Overflow")
    print(f"Đã ghi gói {d}: {len(nodes)} thực thể, {len(edges)} quan hệ")


if __name__ == "__main__":
    main()
