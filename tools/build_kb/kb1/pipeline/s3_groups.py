"""Bước 3: gán mỗi ô con cho ô cha, và đánh dấu nhóm "chọn một".

Thứ tự luật, chắc trước, đoán sau:
  1. frame_heading    ô con nằm trong khung có tiêu đề -> tiêu đề đó
  2. frame_main       khung có ô chính bên trong -> ô chính đó
  3. cluster_heading  chồng ô có chữ rời sát cạnh -> chữ rời đó
  4. connector        chồng ô có đường nối tới ô chính -> ô chính đó
  5. nearest          ô chính gần nhất tính theo cạnh, trong phạm vi MAX_DIST
  6. orphan           không gán

Ghi kb1/out/groups.jsonl và kb1/out/nodes_grouped.jsonl (loại ô sau khi nâng chữ rời thành tiêu đề).
"""
import collections
import csv
import random
import re

import pymupdf

from shared.common import read_jsonl, write_jsonl
from kb1.pipeline.config import (
    CLUSTER_GAP, CONNECTOR_GAP, GOLD_GROUP_SAMPLE, GOLD_PDFS, GOLD_SEED, HEADING_GAP, MAX_DIST, OUT,
    PICK_ONE_RE,
)


def edge_dist(a, b):
    """Khoảng cách giữa hai hình chữ nhật (0 nếu chồng nhau)."""
    dx = max(b.x0 - a.x1, a.x0 - b.x1, 0)
    dy = max(b.y0 - a.y1, a.y0 - b.y1, 0)
    return (dx * dx + dy * dy) ** 0.5


def point_dist(rect, x, y):
    return edge_dist(rect, pymupdf.Rect(x, y, x, y))


def pick_heading(sub, headings):
    """Tiêu đề của ô con trong một nhóm có thể có nhiều tiêu đề.

    Khi phần tử dưới cùng của nhóm là tiêu đề thì tiêu đề nằm dưới các ô con của nó.
    """
    footer = max(h["rect"].y1 for h in headings) >= sub["group_bottom"]
    if footer:
        side = [h for h in headings if h["rect"].y0 >= sub["rect"].y1 - 2]
    else:
        side = [h for h in headings if h["rect"].y1 <= sub["rect"].y0 + 2]
    # gần nhất theo cạnh: hai tiêu đề đặt cạnh nhau ("Layouts", "Elements") chia theo cột
    return min(side or headings, key=lambda h: edge_dist(h["rect"], sub["rect"]))


def build_clusters(units):
    """Gom các đơn vị (khung, ô rời) sát nhau thành chồng ô, bằng union-find."""
    parent = list(range(len(units)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(units):
        for j in range(i + 1, len(units)):
            if edge_dist(a["rect"], units[j]["rect"]) <= CLUSTER_GAP:
                parent[find(i)] = find(j)
    clusters = collections.defaultdict(list)
    for i, unit in enumerate(units):
        clusters[find(i)].append(unit)
    return list(clusters.values())


def cluster_rect(cluster):
    rect = pymupdf.Rect(cluster[0]["rect"])
    for unit in cluster[1:]:
        rect |= unit["rect"]
    return rect


def connected_main(cluster, mains, connectors):
    """Ô chính nối với chồng ô bằng đường nối; nhiều ô thì lấy ô gần nhất."""
    found = []
    for x0, y0, x1, y1 in connectors:
        for (ax, ay), (bx, by) in (((x0, y0), (x1, y1)), ((x1, y1), (x0, y0))):
            if min(point_dist(u["rect"], ax, ay) for u in cluster) > CONNECTOR_GAP:
                continue
            found += [m for m in mains if point_dist(m["rect"], bx, by) <= CONNECTOR_GAP]
    rect = cluster_rect(cluster)
    return min(found, key=lambda m: edge_dist(m["rect"], rect), default=None)


def relation(child, parent, method, dist):
    return {"pdf": child["pdf"], "child": child["label"], "child_id": child["node_id"],
            "child_kind": child["kind"],
            "parent": parent["label"] if parent else None,
            "parent_id": parent["node_id"] if parent else None,
            "parent_kind": parent["kind"] if parent else None,
            "method": method, "dist": round(dist, 1),
            "pick_one": bool(parent and re.search(PICK_ONE_RE, parent["label"], re.I))}


def group_page(nodes, shapes):
    frames = {int(k): pymupdf.Rect(v) for k, v in shapes["frames"].items()}
    connectors = shapes["connectors"]
    for n in nodes:
        n["rect"] = pymupdf.Rect(n["bbox"])
    mains = [n for n in nodes if n["kind"] == "main"]
    subs = [n for n in nodes if n["kind"] == "sub"]

    by_frame = collections.defaultdict(list)
    for n in nodes:
        if n["frame"] is not None and n["kind"] in ("main", "sub", "heading"):
            by_frame[n["frame"]].append(n)

    units = [{"rect": frames[f], "members": members} for f, members in by_frame.items()]
    units += [{"rect": s["rect"], "members": [s]} for s in subs if s["frame"] is None]
    clusters = build_clusters(units)

    loose = [n for n in nodes if n["kind"] in ("free", "section")]
    cluster_heads = collections.defaultdict(list)
    for text in loose:                                  # chữ rời sát chồng ô: tiêu đề của chồng ô
        best = min(range(len(clusters)), default=None,
                   key=lambda i: edge_dist(cluster_rect(clusters[i]), text["rect"]))
        if best is not None and edge_dist(cluster_rect(clusters[best]), text["rect"]) <= HEADING_GAP:
            text["kind"] = "heading"
            cluster_heads[best].append(text)

    rows = []
    for index, cluster in enumerate(clusters):
        members = [m for unit in cluster for m in unit["members"]]
        rect = cluster_rect(cluster)
        inner_mains = [m for m in members if m["kind"] == "main"]
        target = connected_main(cluster, [m for m in mains if m not in inner_mains], connectors)
        if inner_mains:
            outer, outer_method, outer_dist = None, None, 0
        elif target:
            outer, outer_method, outer_dist = target, "connector", edge_dist(target["rect"], rect)
        else:
            near = min(mains, key=lambda m: edge_dist(m["rect"], rect), default=None)
            near_dist = edge_dist(near["rect"], rect) if near else 1e9
            outer, outer_method, outer_dist = ((near, "nearest", near_dist) if near_dist <= MAX_DIST
                                               else (None, "orphan", near_dist))

        def main_for(node):
            if inner_mains:
                best = min(inner_mains, key=lambda m: edge_dist(m["rect"], node["rect"]))
                return best, "frame_main", edge_dist(best["rect"], node["rect"])
            return outer, outer_method, outer_dist

        for unit in cluster:
            unit_heads = sorted((m for m in unit["members"] if m["kind"] == "heading"),
                                key=lambda h: h["rect"].y0)
            loose_heads = sorted(cluster_heads[index], key=lambda h: h["rect"].y0)
            bottom = max(m["rect"].y1 for m in unit["members"])
            cluster_bottom = max([m["rect"].y1 for m in members] + [h["rect"].y1 for h in loose_heads])
            for node in unit["members"]:
                if node["kind"] != "sub":
                    continue
                if unit_heads:
                    node["group_bottom"] = bottom
                    head = pick_heading(node, unit_heads)
                    rows.append(relation(node, head, "frame_heading", edge_dist(head["rect"], node["rect"])))
                    continue
                head = None
                if loose_heads:
                    node["group_bottom"] = cluster_bottom
                    head = pick_heading(node, loose_heads)
                if head and edge_dist(head["rect"], node["rect"]) <= MAX_DIST:
                    rows.append(relation(node, head, "cluster_heading", edge_dist(head["rect"], node["rect"])))
                else:
                    rows.append(relation(node, *main_for(node)))
        for head in [m for m in members if m["kind"] == "heading"] + cluster_heads[index]:
            rows.append(relation(head, *main_for(head)))
    return rows


def write_gold_template(rows):
    """Tạo file để người kiểm điền tay. Không ghi đè; không hiện kết quả máy để tránh thiên lệch."""
    path = OUT / "gold_groups.csv"
    if path.exists():
        return
    pool = sorted({(r["pdf"], r["child"]) for r in rows
                   if r["child_kind"] == "sub" and r["pdf"] in GOLD_PDFS})
    if len(pool) < GOLD_GROUP_SAMPLE:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pdf", "child", "parent_expected"])
        for pdf, child in sorted(random.Random(GOLD_SEED).sample(pool, GOLD_GROUP_SAMPLE)):
            writer.writerow([pdf, child, ""])


def main():
    nodes = read_jsonl(OUT / "nodes.jsonl")
    by_page = collections.defaultdict(list)
    for n in nodes:
        by_page[(n["pdf"], n["page"])].append(n)

    rows = []
    for shapes in read_jsonl(OUT / "shapes.jsonl"):
        rows += group_page(by_page[(shapes["pdf"], shapes["page"])], shapes)
    write_jsonl(OUT / "groups.jsonl", rows)

    for n in nodes:
        n.pop("rect", None)
        n.pop("group_bottom", None)
    write_jsonl(OUT / "nodes_grouped.jsonl", nodes)

    write_gold_template(rows)
    by_method = collections.Counter(r["method"] for r in rows)
    print(f"{len(rows)} quan hệ con -> cha: {dict(by_method)}")


if __name__ == "__main__":
    main()
