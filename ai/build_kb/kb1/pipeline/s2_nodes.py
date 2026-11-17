"""Bước 2: mỗi ô trên sơ đồ thành một nút có nhãn, toạ độ và loại ô.

Ghi kb1/out/nodes.jsonl (nút) và kb1/out/shapes.jsonl (khung nhóm, đầu mút đường nối).
Tiêu đề nhóm có cùng cỡ chữ với ô thường, nên nhận diện bằng vị trí: chữ nằm trực tiếp trong khung.
"""
import csv
import hashlib
import re
import statistics

import pymupdf

from kb1.pipeline.pdfs import selected_pdfs
from shared.common import write_jsonl
from kb1.pipeline.config import (
    CONTAINER_FILLS, LINE_FILLS, LINK_FILLS, MAIN_FILLS, MAX_PAGE_SHARE, MIN_BOX_H, MIN_BOX_W,
    MIN_FRAME_H, MIN_FRAME_W, NOISE_PATTERNS, OUT, PROSE_MIN_WORDS, SECTION_SIZE_RATIO, SOURCES_CSV,
    SUB_FILLS,
)


def rounded(color):
    return tuple(round(c, 2) for c in color) if color else None


def is_noise(text):
    return any(re.search(p, text, re.I) for p in NOISE_PATTERNS)


def is_prose(text):
    words = len(text.split())           # "Advanced Crypto." là nhãn viết tắt, không phải câu văn
    return words >= PROSE_MIN_WORDS or (words >= 4 and text.rstrip().endswith((".", "!")))


def box_kind(fill):
    if fill in MAIN_FILLS:
        return "main"
    if fill in SUB_FILLS:
        return "sub"
    if fill in LINK_FILLS:
        return "link"
    return None


def extract_boxes(page):
    """Ô có nền và khung chỉ có viền, sắp từ nhỏ đến lớn. Bỏ nền trang, dấu chấm, đường nối."""
    limit = page.rect.get_area() * MAX_PAGE_SHARE
    boxes = []
    for d in page.get_drawings():
        rect, fill, stroke = pymupdf.Rect(d["rect"]), rounded(d.get("fill")), rounded(d.get("color"))
        if rect.get_area() > limit:
            continue
        big_enough = rect.width > MIN_BOX_W and rect.height > MIN_BOX_H
        if fill and big_enough and (d["type"] == "fs" or fill not in LINE_FILLS):
            boxes.append({"rect": rect, "fill": fill})     # đường nối chấm có fill nhưng không có viền
        elif (not fill and stroke == (0.0, 0.0, 0.0)
              and rect.width > MIN_FRAME_W and rect.height > MIN_FRAME_H):
            boxes.append({"rect": rect, "fill": (1.0, 1.0, 1.0)})
    return sorted(boxes, key=lambda b: b["rect"].get_area())


def extract_connectors(page):
    """Hai đầu mút của mỗi đường nối (nét liền hoặc chấm)."""
    connectors = []
    for d in page.get_drawings():
        color = rounded(d.get("fill")) if d["type"] == "f" else rounded(d.get("color"))
        if color not in LINE_FILLS or not d["items"]:
            continue
        first, last = d["items"][0], d["items"][-1]
        if first[0] not in ("l", "c") or last[0] not in ("l", "c"):
            continue
        a, b = first[1], last[-1]
        if abs(a.x - b.x) + abs(a.y - b.y) > 5:
            connectors.append([round(a.x, 1), round(a.y, 1), round(b.x, 1), round(b.y, 1)])
    return connectors


def drop_overdrawn(spans):
    """Một số PDF vẽ chồng cùng một chữ hai lần ở cùng vị trí: chỉ giữ một bản."""
    kept = {}
    for s in spans:
        kept.setdefault((s["text"], round(s["rect"].x0), round(s["rect"].y0)), s)
    return list(kept.values())


def extract_spans(page):
    return drop_overdrawn([{"rect": pymupdf.Rect(s["bbox"]), "text": s["text"].strip(), "size": s["size"]}
                           for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
                           for s in l["spans"] if s["text"].strip()])


def innermost(rect, boxes):
    """Chỉ số ô nhỏ nhất chứa tâm của rect. boxes đã sắp từ nhỏ đến lớn."""
    center = (rect.tl + rect.br) / 2
    return next((i for i, b in enumerate(boxes) if b["rect"].contains(center)), None)


def merge_lines(spans):
    """Gộp các dòng liền nhau của cùng một đoạn chữ."""
    merged = []
    for s in sorted(spans, key=lambda s: (s["rect"].y0, s["rect"].x0)):
        for m in merged:
            gap = s["rect"].y0 - m["rect"].y1
            overlap = min(s["rect"].x1, m["rect"].x1) - max(s["rect"].x0, m["rect"].x0)
            if -3 <= gap <= 0.6 * s["size"] and overlap > 0:
                m["text"] += " " + s["text"]
                m["rect"] = m["rect"] | s["rect"]
                break
        else:
            merged.append(dict(s))
    return merged


def extract_page(page, pdf_stem, sha, page_no, start):
    boxes = extract_boxes(page)
    spans = extract_spans(page)
    body_size = statistics.median(s["size"] for s in spans)
    title_size = max(s["size"] for s in spans)

    frames = [i for i, b in enumerate(boxes) if b["fill"] in CONTAINER_FILLS]
    by_box, loose = {}, []
    for s in spans:
        i = innermost(s["rect"], boxes)
        if i is None:
            loose.append(s)
        else:
            by_box.setdefault(i, []).append(s)

    def frame_of(rect, own):
        center = (rect.tl + rect.br) / 2
        return next((i for i in frames if i != own and boxes[i]["rect"].contains(center)
                     and boxes[i]["rect"].get_area() > rect.get_area()), None)

    nodes, n = [], start

    def add(label, kind, rect, fill, size, frame):
        nonlocal n
        n += 1
        nodes.append({"pdf": pdf_stem, "sha256": sha, "page": page_no, "node_id": f"{pdf_stem}#{n}",
                      "label": label, "kind": kind, "bbox": [round(v, 1) for v in rect],
                      "fill": fill, "size": round(size, 1), "frame": frame})

    frame_children, frame_links = {}, set()
    for i, group in sorted(by_box.items()):            # chữ trong ô có màu
        box = boxes[i]
        if box["fill"] in CONTAINER_FILLS:
            continue
        group.sort(key=lambda s: (s["rect"].y0, s["rect"].x0))
        label = " ".join(s["text"] for s in group)
        kind = box_kind(box["fill"])
        if kind is None:
            print(f"  [cảnh báo] {pdf_stem}: màu chưa khai báo {box['fill']}: {label!r}")
            kind = "link"
        if kind in ("main", "sub") and is_noise(label):
            kind = "noise"
        frame = frame_of(box["rect"], i)
        add(label, kind, box["rect"], box["fill"], max(s["size"] for s in group), frame)
        if kind in ("main", "sub"):
            frame_children[frame] = frame_children.get(frame, 0) + 1
        elif kind == "link":
            frame_links.add(frame)

    for i in frames:                                   # chữ nằm trực tiếp trong khung
        lines = merge_lines(by_box.get(i, []))
        for s in lines:
            clean = not is_noise(s["text"]) and not is_prose(s["text"])
            if frame_children.get(i) and clean:
                add(s["text"], "heading", s["rect"], None, s["size"], i)
            elif len(lines) == 1 and i not in frame_links and clean:
                # hộp trắng chỉ có một nhãn, đặt sát chồng ô: Bước 3 sẽ xét thành tiêu đề
                add(s["text"], "free", boxes[i]["rect"], None, s["size"], None)
            else:
                add(s["text"], "noise", s["rect"], None, s["size"], i)

    for s in merge_lines(loose):                       # chữ ngoài mọi ô
        if s["size"] >= title_size:
            kind = "title"
        elif is_noise(s["text"]) or is_prose(s["text"]):
            kind = "noise"
        elif s["size"] >= body_size * SECTION_SIZE_RATIO:
            kind = "section"
        else:
            kind = "free"
        add(s["text"], kind, s["rect"], None, s["size"], None)

    shapes = {"pdf": pdf_stem, "page": page_no,
              "frames": {str(i): [round(v, 1) for v in boxes[i]["rect"]] for i in frames},
              "connectors": extract_connectors(page)}
    return nodes, shapes, n


def update_sha(hashes):
    with open(SOURCES_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        stem = row["uri"].rsplit("/", 1)[-1].removesuffix(".pdf")
        row["sha256"] = hashes.get(stem, row["sha256"])
    with open(SOURCES_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    all_nodes, all_shapes, hashes = [], [], {}
    for pdf in selected_pdfs(__doc__):
        data = pdf.read_bytes()
        hashes[pdf.stem] = hashlib.sha256(data).hexdigest()
        doc = pymupdf.open(stream=data, filetype="pdf")
        count, kinds = 0, {}
        for page_no, page in enumerate(doc, start=1):
            nodes, shapes, count = extract_page(page, pdf.stem, hashes[pdf.stem], page_no, count)
            all_nodes += nodes
            all_shapes.append(shapes)
            for node in nodes:
                kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
        print(f"{pdf.stem}: {count} nút {kinds}")
    write_jsonl(OUT / "nodes.jsonl", all_nodes)
    write_jsonl(OUT / "shapes.jsonl", all_shapes)
    update_sha(hashes)


if __name__ == "__main__":
    main()
