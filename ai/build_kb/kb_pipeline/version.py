"""Thư ký chung, phần 3: so với KB lần trước (diff) và ghi phiên bản KBVersion (Knowledge base.md mục 6, bước 5)."""
import collections
import datetime as dt
import json

DIFF_LIMIT = 200          # số mục tối đa liệt kê cho mỗi loại thay đổi trong kb_diff.json
IGNORED = {"updated_at"}


def node_id(n):
    return (n["label"], n.get("key") or n.get("source_id"))


def edge_id(e):
    return (e["type"], e["src"], e["dst"], e.get("method") if e["type"] == "NEAR" else None)


def _changes(old, new, ident):
    old_by = {ident(x): x for x in old}
    new_by = {ident(x): x for x in new}
    added = sorted(set(new_by) - set(old_by), key=str)
    removed = sorted(set(old_by) - set(new_by), key=str)
    changed = []
    for k in sorted(set(old_by) & set(new_by), key=str):
        fields = sorted(f for f in set(old_by[k]) | set(new_by[k]) - IGNORED
                        if f not in IGNORED and old_by[k].get(f) != new_by[k].get(f))
        if fields:
            changed.append((k, fields))
    return added, removed, changed


def diff(old_nodes, old_edges, nodes, edges):
    """Hàm thuần: thêm, bớt, đổi gì so với lần trước. Trả dict có summary và danh sách (cắt DIFF_LIMIT)."""
    out = {"summary": {}}
    for what, old, new, ident in (("nodes", old_nodes, nodes, node_id), ("edges", old_edges, edges, edge_id)):
        added, removed, changed = _changes(old, new, ident)
        group = (lambda k: k[0])
        out["summary"][what] = {
            "added": dict(collections.Counter(group(k) for k in added)),
            "removed": dict(collections.Counter(group(k) for k in removed)),
            "changed": dict(collections.Counter(group(k) for k, _ in changed)),
            "changed_fields": dict(collections.Counter(f for _, fs in changed for f in fs)),
        }
        out[what] = {"added": [list(k) for k in added[:DIFF_LIMIT]],
                     "removed": [list(k) for k in removed[:DIFF_LIMIT]],
                     "changed": [{"id": list(k), "fields": fs} for k, fs in changed[:DIFF_LIMIT]]}
    out["empty"] = not any(v for s in out["summary"].values() for k, v in s.items() if k != "changed_fields")
    return out


def sources_changed(old_nodes, nodes):
    old = {n["source_id"]: n.get("sha256") for n in old_nodes if n["label"] == "Source"}
    new = {n["source_id"]: n.get("sha256") for n in nodes if n["label"] == "Source"}
    return sorted(s for s in set(old) | set(new) if s not in old or s not in new or old[s] != new[s])


def next_version_id(history, today=None):
    today = (today or dt.date.today()).isoformat()
    used = {v["id"] for v in history}
    vid, n = f"kb-{today}", 2
    while vid in used:
        vid, n = f"kb-{today}-{n}", n + 1
    return vid


def make_version(history, nodes, edges, packs, changes, old_nodes, today=None):
    """KBVersion mới nếu KB đổi (hoặc chưa có phiên bản nào); không đổi thì dùng lại phiên bản cuối."""
    if history and changes["empty"]:
        return history[-1], False
    statuses = collections.Counter(x["status"] for x in [*nodes, *edges] if x.get("label") != "Source")
    version = {
        "id": next_version_id(history, today),
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "n_skills": sum(n["label"] == "Skill" and n["status"] != "rejected" for n in nodes),
        "n_relations": sum(e["status"] != "rejected" for e in edges),
        "n_candidates": statuses["candidate"], "n_accepted": statuses["accepted"],
        "n_review": statuses["review"], "n_rejected": statuses["rejected"],
        "n_provisional": sum(x.get("accepted_by") == "provisional" for x in [*nodes, *edges]),
        "sources_changed": sources_changed(old_nodes, nodes),
        "packs": [f"{p['manifest']['pack_id']}@{p['sha256'][:12]}" for p in packs],
        "diff": json.dumps(changes["summary"], ensure_ascii=False),
        "previous": history[-1]["id"] if history else None,
    }
    return version, True
