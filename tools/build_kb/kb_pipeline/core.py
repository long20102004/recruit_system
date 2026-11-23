"""Thư ký chung, phần 1: đối chiếu thực thể, gộp khẳng định của mọi gói, áp bản vá.

Gói được nạp theo (priority, pack_id). Thực thể của gói trước được coi là "đã có"; gói sau gọi tên, pipeline
tự tìm thực thể:
  1. khoá trùng (sau khi chuẩn hoá) -> cùng thực thể;
  2. tên trùng một alias không dễ nhầm của thực thể đã có -> cùng thực thể ("ReactJS" -> React);
  3. không khớp -> thực thể mới (phải đủ trường bắt buộc), hoặc vào hàng đợi duyệt nếu khẳng định dùng 'ref'.
Alias đã thuộc thực thể khác thì bỏ và ghi vào hàng đợi duyệt: gói trước thắng, không bao giờ có alias trùng.
Alias dễ nhầm được phép chung nhiều thực thể (module match chỉ khớp khi là nguyên phần tử), nhưng một chuỗi không
được vừa là alias thường của thực thể này vừa là alias dễ nhầm của thực thể khác.
"""
import collections

from kb_pipeline.schema import (
    EDGE_ENDS, EDGE_PROPS, EDGE_RESERVED, LEVEL_RANKS, NODE_FIELDS, NODE_RESERVED, REQUIRED_NEW, TRUST_WEIGHT,
)
from shared.common import norm, strip_accents

# Thuộc tính mà nhiều nguồn cho giá trị khác nhau là bình thường (vd. trích dẫn ở trang khác): không báo mâu thuẫn
QUIET_PROPS = {"EVIDENCED_BY": ("page", "snippet")}


class KB:
    def __init__(self, role_groups, sources, pack_origin):
        self.role_groups = list(role_groups)
        self.pack_origin = pack_origin                           # pack_id -> kb_origin
        self.sources = sources                                   # source_id -> Source (đã kèm pack_id)
        self.ents = {label: {} for label in NODE_FIELDS}
        self.free = {label: {} for label in NODE_FIELDS}         # alias thường -> khoá
        self.amb = {label: collections.defaultdict(set) for label in NODE_FIELDS}   # alias dễ nhầm -> {khoá}
        self.redirect = {label: {} for label in NODE_FIELDS}     # khoá đã gộp -> khoá giữ
        self.edges = {}                                          # (type, src, dst, method) -> edge
        self.review = []
        self.info = collections.Counter()
        self.resolved_by_alias = []
        self.pending = []                                        # alias trùng, xét lại sau same_as

    # ------------------------------------------------------------------ tra cứu
    def follow(self, label, key):
        seen = set()
        while key in self.redirect[label] and key not in seen:
            seen.add(key)
            key = self.redirect[label][key]
        return key

    def resolve(self, label, text):
        """Tên, khoá hoặc alias thường -> khoá thực thể; None nếu không có."""
        n = norm(str(text))
        key = self.follow(label, n)
        if key in self.ents[label]:
            return key
        owner = self.free[label].get(n)
        return self.follow(label, owner) if owner else None

    def resolve_end(self, label, text):
        if label == "RoleGroup":
            return next((g for g in self.role_groups if norm(g) == norm(str(text))), None)
        if label == "Source":
            return text if text in self.sources else None
        return self.resolve(label, text)

    def flag(self, kind, pack, **detail):
        self.review.append({"kind": kind, "pack": pack, **detail})

    # ------------------------------------------------------------------ alias
    def add_alias(self, label, key, alias, ambiguous, pack, variant=False):
        if not alias:
            return
        ent = self.ents[label][key]
        owner = self.free[label].get(alias)
        amb_others = self.amb[label].get(alias, set()) - {key}
        clash = (owner and owner != key) or (not ambiguous and amb_others)
        if clash:
            # Chưa kết luận: nếu same_as sau đó gộp hai thực thể này thì không còn trùng (resolve_pending)
            self.pending.append({"label": label, "key": key, "alias": alias, "ambiguous": ambiguous,
                                 "pack": pack, "variant": variant})
            return
        if ambiguous:
            if owner == key:
                del self.free[label][alias]
                ent["aliases"].discard(alias)
            ent["amb"].add(alias)
            self.amb[label][alias].add(key)
        elif alias not in ent["amb"]:
            ent["aliases"].add(alias)
            self.free[label][alias] = key

    def add_aliases(self, label, key, aliases, ambiguous, pack):
        for group, is_amb in ((ambiguous, True), (aliases, False)):
            normed = {norm(a) for a in group if norm(a)}
            for a in sorted(normed):
                self.add_alias(label, key, a, is_amb, pack)
            for a in sorted({strip_accents(a) for a in normed} - normed):
                self.add_alias(label, key, a, is_amb, pack, variant=True)

    def resolve_pending(self):
        """Sau same_as: alias trùng mà hai bên đã thành một thực thể thì nhận, còn lại ghi vào hàng đợi duyệt."""
        pending, self.pending = self.pending, []
        for p in pending:
            label, key, alias = p["label"], self.follow(p["label"], p["key"]), p["alias"]
            if key not in self.ents[label]:
                continue
            owner = self.free[label].get(alias)
            owner = self.follow(label, owner) if owner else None
            amb_others = {self.follow(label, k) for k in self.amb[label].get(alias, set())} - {key}
            if (owner in (None, key)) and (p["ambiguous"] or not amb_others):
                self.add_alias(label, key, alias, p["ambiguous"], p["pack"], p["variant"])
            elif p["variant"]:                    # dạng không dấu tự sinh trùng: bỏ lặng lẽ, chỉ đếm
                self.info["unaccented_alias_skipped"] += 1
            else:
                self.flag("alias_conflict", p["pack"], label=label, alias=alias, proposed_for=key,
                          owned_by=sorted({owner} - {None, key} | amb_others))
        for p in self.pending:                    # add_alias ở trên không được trùng lần nữa
            self.flag("alias_conflict", p["pack"], label=p["label"], alias=p["alias"], proposed_for=p["key"])
        self.pending = []

    # ------------------------------------------------------------------ thực thể
    def weight(self, source_ids, pack_sources):
        ids = source_ids or pack_sources
        return max((TRUST_WEIGHT[self.sources[s]["trust"]] for s in ids if s in self.sources), default=0.0)

    def add_node(self, pack, a, order):
        label, pid = a["label"], pack["manifest"]["pack_id"]
        prio = pack["manifest"]["priority"]
        if a.get("ref"):
            key = self.resolve(label, a["ref"])
            if key is None:
                self.flag("unresolved_node", pid, label=label, ref=a["ref"])
                return
        else:
            key0 = norm(a.get("key") or a["name"])
            key = self.follow(label, key0)
            if key not in self.ents[label]:
                key = self.resolve(label, a["name"])
                if key is not None:
                    self.resolved_by_alias.append({"pack": pid, "label": label, "name": a["name"], "key": key})
            if key is None:
                missing = [f for f in REQUIRED_NEW.get(label, ()) if f not in a]
                if missing:
                    self.flag("new_node_missing_fields", pid, label=label, name=a["name"], missing=missing)
                    return
                if label == "Level" and LEVEL_RANKS.get(a["name"]) != a["rank"]:
                    self.flag("level_off_scale", pid, name=a["name"], rank=a["rank"])
                    return
                key = key0
                self.ents[label][key] = {"label": label, "key": key, "name": a["name"], "aliases": set(),
                                         "amb": set(), "fields": collections.defaultdict(list), "set": {},
                                         "sources": set(), "kb_origin": set(), "status": None,
                                         "merged_from": set(), "pack": pid}
                self.info[f"new_{label}"] += 1
        ent = self.ents[label][key]
        names = [x for x in (a.get("name"), a.get("key")) if x]
        if not a.get("ref") and ent["pack"] == pid:            # tên của chính thực thể này cũng là alias
            names.append(key)
        self.add_aliases(label, key, [*names, *a.get("aliases", [])], a.get("ambiguous_aliases", []), pid)
        w = self.weight(a.get("sources", []), [s["source_id"] for s in pack["manifest"]["sources"]])
        for field, value in a.items():
            if field not in NODE_RESERVED:
                ent["fields"][field].append({"value": value, "weight": w, "rank": (prio, order), "pack": pid,
                                             "override": field in a.get("override", [])})
        ent["sources"] |= set(a.get("sources", []))
        ent["kb_origin"].add(pack["manifest"]["kb_origin"])

    # ------------------------------------------------------------------ quan hệ
    def edge_key(self, kind, src, dst, method=None):
        if kind == "NEAR":
            order = {g: i for i, g in enumerate(self.role_groups)}
            src, dst = sorted((src, dst), key=order.get)
        return (kind, src, dst, method if kind == "NEAR" else None)

    def add_edge(self, pack, e, order):
        pid, prio = pack["manifest"]["pack_id"], pack["manifest"]["priority"]
        kind = e["type"]
        src_label, dst_label = EDGE_ENDS[kind]
        src, dst = self.resolve_end(src_label, e["src"]), self.resolve_end(dst_label, e["dst"])
        if src is None or dst is None:
            self.flag("unresolved_edge", pid, type=kind, src=e["src"], dst=e["dst"],
                      missing=[x for x, ok in ((e["src"], src), (e["dst"], dst)) if ok is None])
            return
        if kind == "PARENT_OF" and src == dst:
            self.info["self_loop_dropped"] += 1
            return
        key = self.edge_key(kind, src, dst, e.get("method"))
        edge = self.edges.setdefault(key, {"type": kind, "src": key[1], "dst": key[2], "sources": [],
                                           "evidence": [], "kb_origin": set(), "props": collections.defaultdict(list),
                                           "rank": (prio, order), "status": None})
        sources = [p["source_id"] for p in e["evidence"]] + list(e.get("sources", []))
        edge["sources"] += [s for s in dict.fromkeys(sources) if s not in edge["sources"]]
        edge["evidence"] += [p for p in e["evidence"] if p not in edge["evidence"]]
        edge["kb_origin"].add(pack["manifest"]["kb_origin"])
        w = self.weight(sources, [])
        for prop, value in e.items():
            if prop not in EDGE_RESERVED:
                edge["props"][prop].append({"value": value, "weight": w, "rank": (prio, order), "pack": pid})

    # ------------------------------------------------------------------ bản vá
    def apply_same_as(self, p, pid):
        label = p["label"]
        drop, keep = self.resolve(label, p["drop"]), self.resolve(label, p["keep"])
        if drop is None or keep is None:
            self.flag("unresolved_patch", pid, op="same_as", label=label, drop=p["drop"], keep=p["keep"])
            return
        if drop == keep:
            self.info["same_as_already_merged"] += 1
            return
        gone, kept = self.ents[label].pop(drop), self.ents[label][keep]
        for a in gone["aliases"]:
            self.free[label][a] = keep
            if a not in kept["amb"]:
                kept["aliases"].add(a)
        for a in gone["amb"]:
            self.amb[label][a].discard(drop)
            self.amb[label][a].add(keep)
            kept["amb"].add(a)
        kept["sources"] |= gone["sources"]
        kept["kb_origin"] |= gone["kb_origin"] | {self.pack_origin[pid]}
        kept["merged_from"] |= {drop} | gone["merged_from"]
        self.redirect[label][drop] = keep
        self.info["same_as"] += 1

    def apply_patch(self, p, pid):
        op = p["op"]
        if op == "drop_edge":
            src_label, dst_label = EDGE_ENDS[p["type"]]
            src, dst = self.resolve_end(src_label, p["src"]), self.resolve_end(dst_label, p["dst"])
            keys = [k for k in self.edges if k[:3] == (p["type"], src, dst)]
            if not keys:
                self.flag("unresolved_patch", pid, op=op, type=p["type"], src=p["src"], dst=p["dst"])
            for k in keys:
                del self.edges[k]
                self.info["drop_edge"] += 1
            return
        label = p["label"]
        key = self.resolve(label, p["ref"])
        if key is None:
            self.flag("unresolved_patch", pid, op=op, label=label, ref=p["ref"])
            return
        ent = self.ents[label][key]
        if op == "reject":
            ent["status"] = "rejected"
        elif op == "ambiguous":
            for a in ent["aliases"] | {key}:
                if self.free[label].get(a) == key:
                    del self.free[label][a]
                ent["amb"].add(a)
                self.amb[label][a].add(key)
            ent["aliases"] = set()
        elif op == "set":
            ent["set"].update(p["fields"])
        self.info[op] += 1

    # ------------------------------------------------------------------ chốt giá trị
    def pick(self, values, what, where):
        """Chọn một giá trị khi nhiều gói khẳng định khác nhau: override (gói sau thắng) > trust cao > gói trước."""
        overrides = [v for v in values if v.get("override")]
        if overrides:
            return max(overrides, key=lambda v: v["rank"])["value"]
        distinct = {repr(v["value"]) for v in values}
        best = min(values, key=lambda v: (-v["weight"], v["rank"]))
        if len(distinct) > 1:
            self.flag("value_conflict", best["pack"], what=what, where=where, chosen=best["value"],
                      values=[{"pack": v["pack"], "value": v["value"], "weight": v["weight"]} for v in values])
        return best["value"]


def run_core(packs, role_groups):
    """Hàm thuần: gói -> KB (chưa chấm điểm). Trả (kb, lỗi chặn)."""
    errors, sources = [], {}
    for pack in packs:
        for s in pack["manifest"]["sources"]:
            sid = s["source_id"]
            if sid in sources and {k: v for k, v in sources[sid].items() if k != "pack_id"} != s:
                errors.append(f"source_id {sid} khai báo khác nhau ở {sources[sid]['pack_id']} và "
                              f"{pack['manifest']['pack_id']}")
            sources.setdefault(sid, {**s, "pack_id": pack["manifest"]["pack_id"]})
    kb = KB(role_groups, sources, {p["manifest"]["pack_id"]: p["manifest"]["kb_origin"] for p in packs})

    for pack in packs:                                         # 1. thực thể
        for i, a in enumerate(pack["nodes"]):
            kb.add_node(pack, a, i)
    for pack in packs:                                         # 2. gộp trùng, trước khi đọc quan hệ
        for p in pack["patches"]:
            if p["op"] == "same_as":
                kb.apply_same_as(p, pack["manifest"]["pack_id"])
    kb.resolve_pending()
    for pack in packs:                                         # 3. quan hệ
        for i, e in enumerate(pack["edges"]):
            kb.add_edge(pack, e, i)
    for pack in packs:                                         # 4. bản vá còn lại, theo thứ tự gói
        for p in pack["patches"]:
            if p["op"] != "same_as":
                kb.apply_patch(p, pack["manifest"]["pack_id"])
    return kb, errors


def finalize(kb):
    """Chốt thực thể và quan hệ thành dict phẳng (định dạng out/kb_nodes.jsonl, kb_edges.jsonl)."""
    nodes = []
    for label, ents in kb.ents.items():
        for key, ent in sorted(ents.items()):
            row = {"label": label, "key": key, "name": ent["name"]}
            for field, values in ent["fields"].items():
                row[field] = kb.pick(values, f"{label}.{field}", key)
            row.update(ent["set"])
            row.update({"aliases": sorted(ent["aliases"]), "ambiguous_aliases": sorted(ent["amb"]),
                        "sources": sorted(ent["sources"]), "kb_origin": sorted(ent["kb_origin"]),
                        "status": ent["status"]})
            if ent["merged_from"]:
                row["merged_from"] = sorted(ent["merged_from"])
            nodes.append(row)
    for sid, s in sorted(kb.sources.items()):
        nodes.append({"label": "Source", **{k: v for k, v in s.items() if k != "pack_id"},
                      "kb_origin": [kb.pack_origin[s["pack_id"]]], "status": "accepted"})

    edges = []
    for key, edge in sorted(kb.edges.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        row = {"type": edge["type"], "src": edge["src"], "dst": edge["dst"], "sources": edge["sources"],
               "evidence": edge["evidence"], "kb_origin": sorted(edge["kb_origin"]), "status": edge["status"],
               "rank": edge["rank"]}
        for prop, values in edge["props"].items():
            if prop in QUIET_PROPS.get(edge["type"], ()):     # nhiều giá trị là bình thường: lấy cái đầu
                row[prop] = min(values, key=lambda v: v["rank"])["value"]
            elif prop == "in_roadmap":
                row[prop] = any(v["value"] for v in values)
            elif prop == "node_kind":
                kinds = {v["value"] for v in values}
                row[prop] = "main" if "main" in kinds else ("sub" if "sub" in kinds else None)
            else:
                row[prop] = kb.pick(values, f"{edge['type']}.{prop}", f"{edge['src']} -> {edge['dst']}")
        for prop in EDGE_PROPS[edge["type"]]:
            row.setdefault(prop, None)
        edges.append(row)
    return nodes, edges
