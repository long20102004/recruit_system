"""KB2, bước 3: biến kb2/data/majors.csv thành nút Major (T6).

Danh mục ngành do Claude tự sinh, chưa đối chiếu với nguồn nào, nên nguồn M01 có trust = low.
key là tên tiếng Anh; tên tiếng Việt và dạng không dấu nằm trong aliases. Ghi kb2/out/kb2_major_nodes.jsonl.
"""
import collections

from kb2.pipeline.config import (
    AMBIGUOUS_MAJOR_ALIASES, MAJOR_GROUPS, MAJOR_SOURCE_ID, MAJORS_CSV, OUT, SOURCES_CSV,
)
from kb2.pipeline.s2_titles import read_csv
from shared.common import norm, strip_accents, write_jsonl  # noqa: F401  (strip_accents dùng lại ở s4_levels)


def build_majors(rows, source):
    """Hàm thuần: trả danh sách nút Major kèm nút Source. Nhóm sai hoặc alias trùng thì dừng."""
    bad_groups = sorted({r["group"] for r in rows} - set(MAJOR_GROUPS))
    if bad_groups:
        raise SystemExit(f"Nhóm ngành không có trong thiết kế: {bad_groups}")
    owners = collections.defaultdict(set)
    nodes = []
    for row in rows:
        key = norm(row["name_en"])
        names = {norm(x) for x in [row["name_en"], row["name_vi"], *row["aliases"].split("|")] if x}
        names |= {strip_accents(x) for x in names}
        for alias in names:
            owners[alias].add(key)
        nodes.append({"label": "Major", "key": key, "name": row["name_en"], "group": row["group"],
                      "aliases": sorted(names - AMBIGUOUS_MAJOR_ALIASES),
                      "ambiguous_aliases": sorted(names & AMBIGUOUS_MAJOR_ALIASES)})
    conflicts = {a: sorted(k) for a, k in owners.items() if len(k) > 1}
    if conflicts:
        raise SystemExit(f"Alias ngành trùng: {conflicts}")
    return nodes + [{"label": "Source", **source}]


def main():
    sources = [s for s in read_csv(SOURCES_CSV) if s["source_id"] == MAJOR_SOURCE_ID]
    if not sources:
        raise SystemExit(f"sources.csv chưa có {MAJOR_SOURCE_ID}")
    nodes = build_majors(read_csv(MAJORS_CSV), sources[0])
    write_jsonl(OUT / "kb2_major_nodes.jsonl", nodes)
    groups = collections.Counter(n["group"] for n in nodes if n["label"] == "Major")
    print(f"Major: {sum(groups.values())}, theo nhóm: {dict(groups)}")


if __name__ == "__main__":
    main()
