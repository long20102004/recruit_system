"""Đọc, ghi và kiểm gói đóng góp. Adapter của từng nguồn chỉ cần gọi write_pack()."""
import hashlib
import json
import pathlib

from kb_pipeline.schema import (
    EDGE_ENDS, EDGE_PROPS, EDGE_RESERVED, NODE_FIELDS, NODE_RESERVED, PATCH_OPS, SOURCE_REQUIRED, TRUST_WEIGHT,
    check_value,
)
from shared.common import read_jsonl, write_jsonl

ROOT = pathlib.Path(__file__).resolve().parents[1]      # build_kb/
PACKS_DIR = ROOT / "packs"
PACK_FILES = ("nodes.jsonl", "edges.jsonl", "patches.jsonl")


def write_pack(pack_id, kb_origin, priority, sources, nodes, edges, patches=(), description="",
               packs_dir=PACKS_DIR):
    """Ghi gói. Kiểm trước khi ghi: gói sai thì dừng, không để lại gói hỏng."""
    manifest = {"pack_id": pack_id, "kb_origin": kb_origin, "priority": priority, "enabled": True,
                "description": description, "sources": list(sources)}
    pack = {"manifest": manifest, "nodes": list(nodes), "edges": list(edges), "patches": list(patches)}
    errors = validate_pack(pack)
    if errors:
        raise SystemExit(f"Gói {pack_id} sai định dạng:\n" + "\n".join(errors[:50]))
    d = packs_dir / pack_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(d / "nodes.jsonl", pack["nodes"])
    write_jsonl(d / "edges.jsonl", pack["edges"])
    write_jsonl(d / "patches.jsonl", pack["patches"])
    return d


def load_pack(d):
    d = pathlib.Path(d)
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    pack = {"manifest": manifest, "dir": str(d)}
    digest = hashlib.sha256()
    for name in PACK_FILES:
        path = d / name
        pack[name.removesuffix(".jsonl")] = read_jsonl(path) if path.exists() else []
        if path.exists():
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))   # cùng sha trên Windows / Linux
    pack["sha256"] = digest.hexdigest()
    return pack


def discover(packs_dir=PACKS_DIR):
    """Mọi gói đang bật, theo (priority, pack_id): gói ưu tiên nhỏ được nạp trước và được coi là đã có."""
    packs = [load_pack(p.parent) for p in sorted(pathlib.Path(packs_dir).glob("*/manifest.json"))]
    packs = [p for p in packs if p["manifest"].get("enabled", True)]
    return sorted(packs, key=lambda p: (p["manifest"].get("priority", 100), p["manifest"]["pack_id"]))


def validate_pack(pack):
    """Kiểm định dạng một gói. Trả danh sách lỗi (rỗng là hợp lệ). Không cần biết KB hiện có."""
    errors = []
    m = pack["manifest"]
    pid = m.get("pack_id", "?")
    for field in ("pack_id", "kb_origin", "priority", "sources"):
        if field not in m:
            errors.append(f"{pid}: manifest thiếu '{field}'")
    source_ids = set()
    for s in m.get("sources", []):
        missing = [f for f in SOURCE_REQUIRED if not s.get(f)]
        if missing:
            errors.append(f"{pid}: Source {s.get('source_id')} thiếu {missing}")
        if s.get("trust") not in TRUST_WEIGHT:
            errors.append(f"{pid}: Source {s.get('source_id')} trust '{s.get('trust')}' không hợp lệ")
        if s.get("source_id") in source_ids:
            errors.append(f"{pid}: source_id {s['source_id']} lặp trong manifest")
        source_ids.add(s.get("source_id"))

    for i, n in enumerate(pack["nodes"], 1):
        where = f"{pid} nodes dòng {i}"
        label = n.get("label")
        if label not in NODE_FIELDS:
            errors.append(f"{where}: nhãn '{label}' không hợp lệ")
            continue
        if bool(n.get("name")) == bool(n.get("ref")):
            errors.append(f"{where}: cần đúng một trong 'name' (tạo hoặc khớp) và 'ref' (phải khớp)")
        for field, value in n.items():
            if field in NODE_RESERVED:
                continue
            rule = NODE_FIELDS[label].get(field)
            if rule is None:
                errors.append(f"{where}: trường '{field}' không có ở nhãn {label}")
            elif not check_value(value, rule):
                errors.append(f"{where}: {field} = {value!r} không hợp lệ")
        for field in ("aliases", "ambiguous_aliases", "sources", "override"):
            if not isinstance(n.get(field, []), list):
                errors.append(f"{where}: '{field}' phải là danh sách")
        unknown = set(n.get("sources", [])) - source_ids
        if unknown:
            errors.append(f"{where}: nguồn {sorted(unknown)} không khai báo trong manifest")

    for i, e in enumerate(pack["edges"], 1):
        where = f"{pid} edges dòng {i}"
        kind = e.get("type")
        if kind not in EDGE_ENDS:
            errors.append(f"{where}: loại quan hệ '{kind}' không hợp lệ")
            continue
        if not e.get("src") or not e.get("dst"):
            errors.append(f"{where}: thiếu src hoặc dst")
        evidence = e.get("evidence") or []
        if not evidence:
            errors.append(f"{where}: thiếu evidence")
        for p in evidence:
            if p.get("source_id") not in source_ids:
                errors.append(f"{where}: evidence trỏ tới nguồn '{p.get('source_id')}' không có trong manifest")
            if not p.get("quote"):
                errors.append(f"{where}: evidence thiếu quote")
        for field, value in e.items():
            if field in EDGE_RESERVED:
                continue
            rule = EDGE_PROPS[kind].get(field)
            if rule is None:
                errors.append(f"{where}: thuộc tính '{field}' không có ở {kind}")
            elif not check_value(value, rule):
                errors.append(f"{where}: {field} = {value!r} không hợp lệ")

    for i, p in enumerate(pack["patches"], 1):
        where = f"{pid} patches dòng {i}"
        op = p.get("op")
        if op not in PATCH_OPS:
            errors.append(f"{where}: op '{op}' không hợp lệ")
            continue
        missing = [f for f in PATCH_OPS[op] if f not in p]
        if missing:
            errors.append(f"{where}: {op} thiếu {missing}")
        if op == "set" and p.get("label") in NODE_FIELDS:
            for field, value in p.get("fields", {}).items():
                rule = NODE_FIELDS[p["label"]].get(field)
                if rule is None or not check_value(value, rule):
                    errors.append(f"{where}: set {field} = {value!r} không hợp lệ ở {p['label']}")
        if op == "drop_edge" and p.get("type") not in EDGE_ENDS:
            errors.append(f"{where}: loại quan hệ '{p.get('type')}' không hợp lệ")
    return errors
