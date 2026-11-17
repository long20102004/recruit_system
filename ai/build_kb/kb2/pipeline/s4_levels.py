"""KB2, bước 4: biến kb2/data/levels.csv thành nút Level (T4).

Thang rank theo Knowledge base.md (Intern 0 đến Lead 5), alias do Claude tự soạn nên nguồn M02 có trust = low.
Level không có quan hệ: module match dò từ bổ nghĩa độc lập với chức danh, "Backend Tech Lead" là Backend
Developer + Lead. Ghi kb2/out/kb2_level_nodes.jsonl.
"""
import collections

from kb2.pipeline.config import AMBIGUOUS_LEVEL_ALIASES, LEVEL_RANKS, LEVEL_SOURCE_ID, LEVELS_CSV, OUT, SOURCES_CSV
from kb2.pipeline.s2_titles import read_csv
from kb2.pipeline.s3_majors import strip_accents
from shared.common import norm, write_jsonl


def build_levels(rows, source):
    """Hàm thuần: trả danh sách nút Level kèm nút Source. Lệch thang của thiết kế hoặc alias trùng thì dừng."""
    scale = {r["name"]: int(r["rank"]) for r in rows}
    if scale != LEVEL_RANKS or len(rows) != len(LEVEL_RANKS):
        raise SystemExit(f"Thang cấp bậc lệch thiết kế: {scale}")
    owners = collections.defaultdict(set)
    nodes = []
    for row in rows:
        key = norm(row["name"])
        names = {norm(x) for x in [row["name"], *row["aliases"].split("|")] if x}
        names |= {strip_accents(x) for x in names}
        for alias in names:
            owners[alias].add(key)
        nodes.append({"label": "Level", "key": key, "name": row["name"], "rank": int(row["rank"]),
                      "aliases": sorted(names - AMBIGUOUS_LEVEL_ALIASES),
                      "ambiguous_aliases": sorted(names & AMBIGUOUS_LEVEL_ALIASES)})
    conflicts = {a: sorted(k) for a, k in owners.items() if len(k) > 1}
    if conflicts:
        raise SystemExit(f"Alias cấp bậc trùng: {conflicts}")
    return nodes + [{"label": "Source", **source}]


def main():
    sources = [s for s in read_csv(SOURCES_CSV) if s["source_id"] == LEVEL_SOURCE_ID]
    if not sources:
        raise SystemExit(f"sources.csv chưa có {LEVEL_SOURCE_ID}")
    nodes = build_levels(read_csv(LEVELS_CSV), sources[0])
    write_jsonl(OUT / "kb2_level_nodes.jsonl", nodes)
    print(f"Level: {len(nodes) - 1}")


if __name__ == "__main__":
    main()
