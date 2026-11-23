"""Thư ký chung, phần 2: luật cho quan hệ, NEAR computed, chấm điểm, kiểm tra chặn.

Luật quan hệ (vi phạm -> status = review, ghi vào hàng đợi duyệt, không xuất cho module match):
  - PARENT_OF chỉ nối hai kỹ năng technology (Knowledge base.md 2.1: "B được xây trên A").
  - PARENT_OF không có vòng: mỗi vòng bỏ cạnh yếu nhất (confidence thấp nhất, rồi gói mới nhất).
  - Quan hệ chạm thực thể bị loại -> rejected.
Chấm điểm (mục 6): confidence = 1 − Π(1 − w_trust), mỗi publisher tính một lần (lấy trust cao nhất).
  Quan hệ accepted khi có ≥ 2 publisher độc lập hoặc 1 nguồn trust = high; nguồn generated không tính là độc lập.
  Thực thể accepted khi có ít nhất một nguồn không tự sinh, trust medium trở lên.
  Chính sách "provisional" (mặc định tạm thời, schema.ACCEPT_POLICY): cái không qua luật trên vẫn accepted, ghi
  accepted_by = "provisional"; cái qua luật ghi accepted_by = "rule". rejected và review không đổi.
  Category chưa có sibling_ok (người duyệt đặt) nhận tạm sibling_ok_suggest, ghi sibling_ok_by = "provisional".
"""
import collections
import itertools

from kb_pipeline.schema import ACCEPT_POLICIES, ACCEPT_POLICY, EDGE_ENDS, GENERATED, TRUST_WEIGHT

LIVE = (None, "candidate", "accepted")


def live(e):
    return e["status"] in LIVE


def confidence(source_ids, sources):
    best = {}
    for sid in source_ids:
        s = sources.get(sid)
        if s:
            best[s["publisher"]] = max(best.get(s["publisher"], 0), TRUST_WEIGHT[s["trust"]])
    rest = 1.0
    for w in best.values():
        rest *= 1 - w
    return round(1 - rest, 3)


def accepted_by_rule(source_ids, sources):
    real = [sources[s] for s in source_ids if s in sources and sources[s]["type"] != GENERATED]
    return len({s["publisher"] for s in real}) >= 2 or any(s["trust"] == "high" for s in real)


def find_cycle(pairs):
    graph = collections.defaultdict(list)
    for a, b in pairs:
        graph[a].append(b)
    color = {}

    def dfs(u, stack):
        color[u] = 1
        stack.append(u)
        for v in graph[u]:
            if color.get(v) == 1:
                return stack[stack.index(v):] + [v]
            if not color.get(v):
                found = dfs(v, stack)
                if found:
                    return found
        stack.pop()
        color[u] = 2
        return None

    for u in list(graph):
        if not color.get(u):
            found = dfs(u, [])
            if found:
                return found
    return None


def near_computed(edges, role_groups):
    """NEAR computed: cosine (Ochiai) |A∩B| / sqrt(|A|·|B|) trên tập kỹ năng USED_IN của hai nhóm.

    Jaccard (cũ) bị nhóm lớn kéo xuống (Backend–Fullstack 0,038); cosine ít lệch theo cỡ nhóm hơn. Vẫn không cùng
    thang với ma trận M giả thuyết, nên Rerank ưu tiên method = hypothesis khi có cả hai.
    """
    skills, srcs = collections.defaultdict(set), collections.defaultdict(set)
    for e in edges:
        if e["type"] == "USED_IN" and live(e):
            skills[e["dst"]].add(e["src"])
            srcs[e["dst"]].update(e["sources"])
    return [{"type": "NEAR", "src": a, "dst": b, "sources": sorted(srcs[a] | srcs[b]), "evidence": [],
             "kb_origin": ["pipeline"], "status": "candidate", "method": "computed",
             "m": round(len(skills[a] & skills[b]) / (len(skills[a]) * len(skills[b])) ** 0.5, 3),
             "shared_skills": len(skills[a] & skills[b])}
            for a, b in itertools.combinations(role_groups, 2) if skills[a] and skills[b]]


def decide(ok, policy):
    """(status, accepted_by) cho một thứ còn sống chưa có status."""
    if ok:
        return "accepted", "rule"
    return ("accepted", "provisional") if policy == "provisional" else ("candidate", None)


def apply_rules(nodes, edges, sources, role_groups, policy=ACCEPT_POLICY):
    """Sửa tại chỗ status của quan hệ, thêm NEAR computed, chấm điểm. Trả (edges, review)."""
    if policy not in ACCEPT_POLICIES:
        raise ValueError(f"policy phải là một trong {ACCEPT_POLICIES}: {policy}")
    review = []
    by_key = {(n["label"], n.get("key") or n.get("source_id")): n for n in nodes}
    rejected = {k for k, n in by_key.items() if n["status"] == "rejected"}
    for e in edges:
        src_label, dst_label = EDGE_ENDS[e["type"]]
        if (src_label, e["src"]) in rejected or (dst_label, e["dst"]) in rejected:
            e["status"] = "rejected"
        e["confidence"] = confidence(e["sources"], sources)

    categories = {n["key"] for n in nodes if n["label"] == "Category"}
    for e in edges:
        if e["type"] != "PARENT_OF" or not live(e):
            continue
        types = (by_key[("Skill", e["src"])].get("type"), by_key[("Skill", e["dst"])].get("type"))
        if types != ("technology", "technology"):
            e["status"] = "review"
            hint = "dùng IN_CATEGORY" if e["src"] in categories else "bỏ, hoặc sửa type nếu đúng là công nghệ"
            review.append({"kind": "parent_of_type", "src": e["src"], "dst": e["dst"], "types": list(types),
                           "sources": e["sources"], "hint": hint})

    while True:
        live_parent = {(e["src"], e["dst"]): e for e in edges if e["type"] == "PARENT_OF" and live(e)}
        cycle = find_cycle(live_parent)
        if not cycle:
            break
        ring = [live_parent[(a, b)] for a, b in zip(cycle, cycle[1:])]
        weakest = min(ring, key=lambda e: (e["confidence"], tuple(-x for x in e.get("rank", (0, 0)))))
        weakest["status"] = "review"
        review.append({"kind": "parent_of_cycle", "cycle": cycle, "dropped": [weakest["src"], weakest["dst"]],
                       "sources": weakest["sources"]})

    edges = [e for e in edges if not (e["type"] == "NEAR" and e.get("method") == "computed")]
    edges += near_computed(edges, role_groups)

    evidenced = collections.defaultdict(set)
    for e in edges:
        e.pop("rank", None)
        if e["type"] == "EVIDENCED_BY":
            evidenced[e["src"]].add(e["dst"])
        if e["status"] in (None, "candidate"):
            if e["type"] == "EVIDENCED_BY":
                s = sources.get(e["dst"], {})
                ok = s.get("type") != GENERATED and s.get("trust") in ("medium", "high")
            elif e["type"] == "NEAR" and e.get("method") == "computed":
                ok = False
            else:
                ok = accepted_by_rule(e["sources"], sources)
            e["status"], by = decide(ok, policy)
            if by:
                e["accepted_by"] = by
        e["confidence"] = confidence(e["sources"], sources)
    for n in nodes:
        if n["label"] == "Source":
            continue
        ids = set(n.get("sources", [])) | (evidenced[n["key"]] if n["label"] == "Skill" else set())
        n["sources"] = sorted(ids)
        n["confidence"] = confidence(ids, sources)
        if n["status"] is None:
            real = [sources[s] for s in ids if s in sources and sources[s]["type"] != GENERATED]
            n["status"], by = decide(any(s["trust"] in ("medium", "high") for s in real), policy)
            if by:
                n["accepted_by"] = by
        # sibling_ok là quyết định của người duyệt; provisional nhận tạm đề xuất
        if (policy == "provisional" and n["label"] == "Category" and n.get("sibling_ok") is None
                and n.get("sibling_ok_suggest") is not None and n["status"] == "accepted"):
            n["sibling_ok"], n["sibling_ok_by"] = n["sibling_ok_suggest"], "provisional"
    return edges, review


def blocking_checks(nodes, edges, role_groups):
    """Các lỗi không được phép có trong KB ghi ra (Knowledge base.md mục 10). Rỗng là đạt."""
    ids = collections.defaultdict(set, {"RoleGroup": set(role_groups)})
    free, amb = collections.defaultdict(set), collections.defaultdict(set)
    for n in nodes:
        ids[n["label"]].add(n.get("key") or n.get("source_id"))
        if n["label"] == "Source" or n["status"] == "rejected":
            continue
        for a in n.get("aliases", []):
            free[(n["label"], a)].add(n["key"])
        for a in n.get("ambiguous_aliases", []):
            amb[(n["label"], a)].add(n["key"])
    conflicts = {f"{label}: {a}": sorted(keys | amb.get((label, a), set()))
                 for (label, a), keys in free.items() if len(keys | amb.get((label, a), set())) > 1}
    dangling = [[e["type"], e["src"], e["dst"]] for e in edges
                if e["src"] not in ids[EDGE_ENDS[e["type"]][0]] or e["dst"] not in ids[EDGE_ENDS[e["type"]][1]]]
    cycle = find_cycle({(e["src"], e["dst"]) for e in edges if e["type"] == "PARENT_OF" and live(e)})
    return {k: v for k, v in {"alias_conflicts": conflicts, "dangling_edges": dangling,
                              "parent_of_cycle": cycle}.items() if v}
