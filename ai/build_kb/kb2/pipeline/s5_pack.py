"""KB2, bước 5: đóng gói KB2 thành gói đóng góp packs/kb2-itviec/ cho thư ký chung (kb_pipeline).

Chỉ đổi định dạng: đọc kb2/out/kb2_nodes.jsonl (JobTitle), kb2_major_nodes.jsonl (Major), kb2_level_nodes.jsonl
(Level), kb2_edges.jsonl (MAPS_TO). Nguồn của mỗi thực thể là Source đi cùng file đó (W01, M01, M02).
Chạy sau s2, s3, s4: python -m kb2.pipeline.s5_pack
"""
from kb2.pipeline.config import OUT
from kb_pipeline.packs import write_pack
from shared.common import read_jsonl

PACK_ID, PRIORITY = "kb2-itviec", 20
NODE_FILES = ("kb2_nodes.jsonl", "kb2_major_nodes.jsonl", "kb2_level_nodes.jsonl")


def to_pack(files, edges):
    """Hàm thuần: files = [[nút của một file, kèm nút Source]] -> (sources, nodes, edges) theo định dạng gói."""
    sources, nodes = [], []
    for rows in files:
        file_sources = [r for r in rows if r["label"] == "Source"]
        sources += [{k: v for k, v in s.items() if k != "label"} for s in file_sources]
        ids = [s["source_id"] for s in file_sources]
        nodes += [{**r, "sources": ids} for r in rows if r["label"] != "Source"]
    for n in nodes:
        if n.get("itviec_group") is None:
            n.pop("itviec_group", None)
    return sources, nodes, [{k: v for k, v in e.items() if k != "sources"} for e in edges]


def main():
    sources, nodes, edges = to_pack([read_jsonl(OUT / f) for f in NODE_FILES], read_jsonl(OUT / "kb2_edges.jsonl"))
    d = write_pack(PACK_ID, "KB2", PRIORITY, sources, nodes, edges,
                   description="KB2: chức danh ITviec (W01), ngành học tự sinh (M01), alias cấp bậc tự soạn (M02)")
    print(f"Đã ghi gói {d}: {len(nodes)} thực thể, {len(edges)} quan hệ")


if __name__ == "__main__":
    main()
