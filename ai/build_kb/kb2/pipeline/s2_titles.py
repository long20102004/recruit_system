"""KB2, bước 2: biến chức danh ITviec thành nút JobTitle và quan hệ MAPS_TO.

key là tên tiếng Anh; tên tiếng Việt chỉ nằm trong aliases. Ghi kb2/out/kb2_nodes.jsonl, kb2_edges.jsonl,
kb2_checks.json.
"""
import collections
import csv
import json

from shared.common import norm, write_jsonl
from kb2.pipeline.config import (
    AMBIGUOUS_TITLE_ALIASES, OUT, ROLE_GROUPS, SOURCES_CSV, TITLE_MAP_CSV, TITLE_SOURCE_ID,
    TITLES_RAW_CSV,
)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check_map(raw, mapping):
    """Mỗi cặp phải đúng một chức danh đã cào ở mỗi ngôn ngữ, cùng nhóm. Trả danh sách lỗi."""
    errors = []
    for lang, field in (("vi", "name_vi"), ("en", "name_en")):
        scraped = collections.Counter((r["group"], r["name"]) for r in raw if r["lang"] == lang)
        mapped = collections.Counter((m["group"], m[field]) for m in mapping)
        errors += [f"{lang}: chưa có trong bảng ghép: {x}" for x in scraped - mapped]
        errors += [f"{lang}: không có trên trang: {x}" for x in mapped - scraped]
    return errors


def build_titles(raw, mapping, source):
    """Hàm thuần: trả (nodes, edges, checks). Bảng ghép sai với dữ liệu đã cào thì dừng."""
    errors = check_map(raw, mapping)
    bad_roles = {g for m in mapping for g in m["role_groups"].split("|") if g and g not in ROLE_GROUPS}
    if bad_roles:
        errors.append(f"nhóm vai trò không có trong thiết kế: {sorted(bad_roles)}")
    if errors:
        raise SystemExit("Bảng ghép chức danh sai:\n" + "\n".join(errors))

    owners = collections.defaultdict(set)
    nodes, edges = [], []
    for m in mapping:
        name = m["canonical"] or m["name_en"]
        key = norm(name)
        names = {norm(x) for x in [name, m["name_en"], m["name_vi"], *m["aliases"].split("|")] if x}
        for alias in names:
            owners[alias].add(key)
        nodes.append({"label": "JobTitle", "key": key, "name": name, "itviec_group": m["group"],
                      "aliases": sorted(names - AMBIGUOUS_TITLE_ALIASES),
                      "ambiguous_aliases": sorted(names & AMBIGUOUS_TITLE_ALIASES)})
        proof = {"source_id": source["source_id"], "page": 1, "quote": f"{m['group']} > {m['name_en']}"}
        edges += [{"type": "MAPS_TO", "src": key, "dst": group, "method": "manual",
                   "sources": [source["source_id"]], "evidence": [proof]}
                  for group in m["role_groups"].split("|") if group]

    mapped = {e["src"] for e in edges}
    checks = {"alias_conflicts": {a: sorted(k) for a, k in owners.items() if len(k) > 1},
              "duplicate_keys": [k for k, n in collections.Counter(x["key"] for x in nodes).items() if n > 1],
              "titles_without_role_group": sorted(n["key"] for n in nodes if n["key"] not in mapped)}
    return nodes + [{"label": "Source", **source}], edges, checks


def main():
    sources = [s for s in read_csv(SOURCES_CSV) if s["source_id"] == TITLE_SOURCE_ID]
    if not sources:
        raise SystemExit(f"sources.csv chưa có {TITLE_SOURCE_ID}")
    nodes, edges, checks = build_titles(read_csv(TITLES_RAW_CSV), read_csv(TITLE_MAP_CSV), sources[0])
    if checks["alias_conflicts"] or checks["duplicate_keys"]:
        raise SystemExit(f"Alias hoặc key trùng: {checks}")
    write_jsonl(OUT / "kb2_nodes.jsonl", nodes)
    write_jsonl(OUT / "kb2_edges.jsonl", edges)
    (OUT / "kb2_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JobTitle: {len(nodes) - 1}, MAPS_TO: {len(edges)}, "
          f"chưa có nhóm vai trò: {len(checks['titles_without_role_group'])}")


if __name__ == "__main__":
    main()
