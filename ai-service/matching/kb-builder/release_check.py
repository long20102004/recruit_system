"""Kiểm một bản chụp trước khi phát hành cho module match (I02).

    python release_check.py out/snapshot/kb-2026-11-24 --prev out/snapshot/kb-2026-11-21-4

So với bản đang dùng: kỹ năng thêm / bớt, đổi tên hiển thị, alias chuyển chủ, skill_id đổi nghĩa
(cùng skill_id nhưng tên chuẩn hoá và mọi alias đều khác: dấu hiệu cấp lại id sai), tên kỹ năng technology
còn viết thường toàn bộ. Ghi `release_check.md` trong thư mục bản chụp. Mã thoát 1 khi có skill_id đổi nghĩa
(chặn phát hành: `reprocess cv --from A5` giữ vector dựa vào skill_id ổn định).
"""

import argparse
import json
import pathlib
import re
import sys

from shared.common import norm


def load(d):
    d = pathlib.Path(d)
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    skills = {}
    with open(d / "skill_ontology.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                skills[r["skill_id"]] = r
    return manifest, skills


def compare(prev, cur):
    """prev, cur: {skill_id: dòng skill_ontology}. Trả dict các danh sách thay đổi (hàm thuần)."""
    added = sorted(set(cur) - set(prev))
    removed = sorted(set(prev) - set(cur))
    renamed, repurposed = [], []
    for sid in sorted(set(prev) & set(cur)):
        a, b = prev[sid], cur[sid]
        if a["name"] != b["name"]:
            renamed.append((sid, a["name"], b["name"]))
        same_key = norm(a["name"]) == norm(b["name"])
        shared_alias = set(a["aliases"]) & set(b["aliases"])
        if not same_key and not shared_alias:
            repurposed.append((sid, a["name"], b["name"]))
    owner_prev = {al: sid for sid, r in prev.items() for al in r["aliases"]}
    owner_cur = {al: sid for sid, r in cur.items() for al in r["aliases"]}
    moved = sorted((al, owner_prev[al], owner_cur[al]) for al in set(owner_prev) & set(owner_cur)
                   if owner_prev[al] != owner_cur[al])
    lower_tech = sorted(r["name"] for r in cur.values()
                        if r["type"] == "technology" and r["name"] == r["name"].lower() and re.search("[a-z]", r["name"]))
    return {"added": added, "removed": removed, "renamed": renamed, "repurposed": repurposed,
            "alias_moved": moved, "lowercase_technology": lower_tech}


def report(version, prev_version, res, cur):
    name = lambda sid: cur.get(sid, {}).get("name", sid)  # noqa: E731
    lines = [f"# Kiểm phát hành {version}", "", f"So với: `{prev_version}`", "",
             "| Mục | Số |", "| --- | --- |"]
    for k, label in [("added", "kỹ năng thêm"), ("removed", "kỹ năng bớt"), ("renamed", "đổi tên hiển thị"),
                     ("alias_moved", "alias chuyển chủ"), ("repurposed", "**skill_id đổi nghĩa (chặn)**"),
                     ("lowercase_technology", "technology còn viết thường")]:
        lines.append(f"| {label} | {len(res[k])} |")
    lines += ["", "## skill_id đổi nghĩa", ""] + ([f"- {s}: `{a}` -> `{b}`" for s, a, b in res["repurposed"]] or ["(không)"])
    lines += ["", "## Đổi tên hiển thị", ""] + ([f"- {s}: `{a}` -> `{b}`" for s, a, b in res["renamed"]] or ["(không)"])
    lines += ["", "## Alias chuyển chủ", ""] + ([f"- `{al}`: {a} -> {b}" for al, a, b in res["alias_moved"]] or ["(không)"])
    lines += ["", "## Kỹ năng thêm / bớt", ""] + [f"- + {s} {name(s)}" for s in res["added"]] + \
             [f"- - {s}" for s in res["removed"]]
    lines += ["", "## Technology còn viết thường (xem có cần `display` ở kb3/data/skill_fixes.csv)", "",
              ", ".join(res["lowercase_technology"]) or "(không)", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Kiểm bản chụp KB trước khi phát hành")
    ap.add_argument("snapshot")
    ap.add_argument("--prev", required=True, help="bản chụp đang dùng ở module match")
    args = ap.parse_args()
    m_cur, cur = load(args.snapshot)
    m_prev, prev = load(args.prev)
    res = compare(prev, cur)
    out = pathlib.Path(args.snapshot) / "release_check.md"
    out.write_text(report(m_cur["ontology_version"], m_prev["ontology_version"], res, cur), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in res.items()}, ensure_ascii=False), "->", out)
    return 1 if res["repurposed"] else 0


if __name__ == "__main__":
    sys.exit(main())
