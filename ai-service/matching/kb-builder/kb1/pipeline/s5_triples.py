"""Bước 5: biến nhóm và loại nhãn thành nút, quan hệ ứng viên theo Knowledge base.md.

Ghi kb1/out/kb1_nodes.jsonl, kb1/out/kb1_edges.jsonl, kb1/out/kb1_checks.json.
"""
import collections
import csv
import json
import re

import pymupdf

from shared.common import norm, read_jsonl, write_jsonl
from kb1.pipeline.config import (
    AMBIGUOUS_ALIASES, OUT, PDF_DIR, PLATFORM_PARENTS, ROADMAPS, SO_REPORT_CSV,
    SO_SYNONYMS_CSV, SOURCES_CSV,
)
from kb1.pipeline.so_aliases import apply_so_aliases, load_synonyms, write_report
from kb_pipeline.quality import find_cycle as find_parent_cycle

SKILL_TYPES = ("technology", "concept")


def load_sources():
    with open(SOURCES_CSV, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def stem_of(source):
    return source["uri"].rsplit("/", 1)[-1].removesuffix(".pdf")


def is_parent_of(parent_key, child_key):
    """Tên con chứa nguyên tên cha, hoặc cha là ngôn ngữ/nền tảng."""
    if parent_key == child_key:
        return False
    contains = re.search(rf"(?<!\w){re.escape(parent_key)}(?!\w)", child_key)
    return bool(contains) or parent_key in PLATFORM_PARENTS


def find_cycle(edges):
    """Trả một vòng PARENT_OF nếu có, ngược lại None."""
    return find_parent_cycle({(e["src"], e["dst"]) for e in edges if e["type"] == "PARENT_OF"})


def alias_conflicts(kb_nodes):
    """Alias, kể cả alias dễ nhầm, thuộc từ hai kỹ năng trở lên (Knowledge base.md, mục 4)."""
    owners = collections.defaultdict(set)
    for node in kb_nodes:
        if node["label"] == "Skill":
            for alias in [*node["aliases"], *node["ambiguous_aliases"]]:
                owners[alias].add(node["key"])
    return {a: sorted(k) for a, k in owners.items() if len(k) > 1}


def build(nodes, groups, labels, sources):
    """Hàm thuần: trả (kb_nodes, kb_edges, checks)."""
    label_of = {l["key"]: l for l in labels}
    source_of = {stem_of(s): s["source_id"] for s in sources}

    def info(text):
        return label_of.get(norm(text), {"type": "unknown", "canonical": ""})

    def skill_key(text):
        return norm(info(text)["canonical"] or text)

    # --- Skill ---
    names = collections.defaultdict(collections.Counter)
    types = collections.defaultdict(collections.Counter)
    aliases = collections.defaultdict(set)
    node_kinds = collections.defaultdict(set)         # (skill, pdf) -> {main, sub}
    for n in nodes:
        if n["kind"] not in ("main", "sub") or info(n["label"])["type"] not in SKILL_TYPES:
            continue
        key = skill_key(n["label"])
        names[key][info(n["label"])["canonical"] or n["label"]] += 1
        types[key][info(n["label"])["type"]] += 1
        aliases[key].update({norm(n["label"]), key})
        node_kinds[(key, n["pdf"])].add(n["kind"])

    kb_nodes = []
    ambiguous = {}
    for key in sorted(names):
        bad = sorted(aliases[key] & AMBIGUOUS_ALIASES)
        if bad:
            ambiguous[key] = bad
        kb_nodes.append({"label": "Skill", "key": key, "name": names[key].most_common(1)[0][0],
                         "type": types[key].most_common(1)[0][0],
                         "aliases": sorted(aliases[key] - AMBIGUOUS_ALIASES),
                         "ambiguous_aliases": bad})

    # --- Category: nhãn category, hoặc cha có từ 2 con là kỹ năng ---
    rows = [r for r in groups if r["child_kind"] == "sub" and r["parent"]
            and skill_key(r["child"]) in names]
    children = collections.defaultdict(set)
    for r in rows:
        children[norm(r["parent"])].add(skill_key(r["child"]))

    def category_ok(parent):
        kind = info(parent)["type"]
        if kind == "category":
            return True
        return kind in SKILL_TYPES and len(children[norm(parent)]) >= 2

    def category_key(parent):
        return norm(info(parent)["canonical"] or parent)

    categories = {}
    for r in rows:
        if category_ok(r["parent"]):
            key = category_key(r["parent"])
            entry = categories.setdefault(key, {"label": "Category", "key": key,
                                                "name": info(r["parent"])["canonical"] or r["parent"],
                                                "sibling_ok_suggest": False})
            entry["sibling_ok_suggest"] = entry["sibling_ok_suggest"] or r["pick_one"]
    kb_nodes += [categories[k] for k in sorted(categories)]

    # --- Quan hệ: gộp theo (loại, đầu, cuối) ---
    edges = {}

    def edge(kind, src, dst, source_id, **extra):
        e = edges.setdefault((kind, src, dst), {"type": kind, "src": src, "dst": dst,
                                                "sources": [], "evidence": [], **extra})
        if source_id not in e["sources"]:
            e["sources"].append(source_id)
        return e

    dropped = 0
    for r in rows:
        source_id = source_of[r["pdf"]]
        child = skill_key(r["child"])
        proof = {"source_id": source_id, "page": 1, "quote": f"{r['parent']} > {r['child']}"}
        parent_type = info(r["parent"])["type"]
        parent_skill = skill_key(r["parent"])
        if (parent_type == "technology" and parent_skill in names
                and types[child].most_common(1)[0][0] == "technology"
                and is_parent_of(parent_skill, child)):
            e = edge("PARENT_OF", parent_skill, child, source_id)
        elif category_ok(r["parent"]):
            e = edge("IN_CATEGORY", child, category_key(r["parent"]), source_id)
        else:
            dropped += 1
            continue
        if proof not in e["evidence"]:
            e["evidence"].append(proof)

    parent_by_id = {r["child_id"]: r["parent"] for r in groups}
    for n in nodes:
        if n["kind"] not in ("main", "sub") or info(n["label"])["type"] not in SKILL_TYPES:
            continue
        key, source_id = skill_key(n["label"]), source_of[n["pdf"]]
        parent = parent_by_id.get(n["node_id"])
        snippet = f"{parent} > {n['label']}" if parent else n["label"]
        e = edge("EVIDENCED_BY", key, source_id, source_id, page=n["page"], snippet=snippet)
        e["evidence"] = [{"source_id": source_id, "page": n["page"], "quote": e["snippet"]}]
        kind, roles = ROADMAPS[n["pdf"]]
        if kind != "role":
            continue
        for role in roles:
            e = edge("USED_IN", key, role, source_id, in_roadmap=True, node_kind="sub")
            if "main" in node_kinds[(key, n["pdf"])]:
                e["node_kind"] = "main"

    kb_edges = [edges[k] for k in sorted(edges)]

    checks = {"alias_conflicts": alias_conflicts(kb_nodes),
              "ambiguous_aliases": ambiguous,
              "parent_of_cycle": find_cycle(kb_edges),
              "dropped_relations": dropped}
    return kb_nodes, kb_edges, checks


def check_quotes(edges):
    """Mỗi vế của quote phải là chuỗi con của chữ trong PDF (Knowledge base.md, mục 3)."""
    texts = {}
    for path in sorted(PDF_DIR.glob("*.pdf")):
        texts[path.stem] = norm(" ".join(p.get_text() for p in pymupdf.open(path)))
    stem_of_source = {s["source_id"]: stem_of(s) for s in load_sources()}
    failed = []
    for e in edges:
        for proof in e["evidence"]:
            text = texts[stem_of_source[proof["source_id"]]]
            if not all(norm(part) in text for part in proof["quote"].split(" > ")):
                failed.append(proof["quote"])
    return sorted(set(failed))


def main():
    sources = load_sources()
    nodes = read_jsonl(OUT / "nodes_grouped.jsonl")
    kb_nodes, kb_edges, checks = build(nodes, read_jsonl(OUT / "groups.jsonl"),
                                       read_jsonl(OUT / "labels.jsonl"), sources)
    so_report, checks["so_aliases"] = apply_so_aliases(kb_nodes, load_synonyms(SO_SYNONYMS_CSV))
    write_report(SO_REPORT_CSV, so_report)
    checks["alias_conflicts"] = alias_conflicts(kb_nodes)
    checks["ambiguous_aliases"] = {n["key"]: n["ambiguous_aliases"] for n in kb_nodes
                                   if n["label"] == "Skill" and n["ambiguous_aliases"]}
    used = {n["pdf"] for n in nodes}
    kb_nodes += [{"label": "Source", **s, "uri": s["uri"]} for s in sources if stem_of(s) in used]
    checks["quotes_not_in_pdf"] = check_quotes(kb_edges)

    write_jsonl(OUT / "kb1_nodes.jsonl", kb_nodes)
    write_jsonl(OUT / "kb1_edges.jsonl", kb_edges)
    (OUT / "kb1_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Nút: {dict(collections.Counter(n['label'] for n in kb_nodes))}")
    print(f"Quan hệ: {dict(collections.Counter(e['type'] for e in kb_edges))}")
    print(f"Kiểm tra: {len(checks['alias_conflicts'])} alias trùng, "
          f"vòng PARENT_OF: {checks['parent_of_cycle']}, "
          f"{len(checks['quotes_not_in_pdf'])} quote không có trong PDF, "
          f"{checks['dropped_relations']} quan hệ bỏ vì cha chỉ có 1 con")
    print(f"Alias từ Stack Overflow: {checks['so_aliases']}, chi tiết ở {SO_REPORT_CSV.name}")


if __name__ == "__main__":
    main()
