"""Pipeline chung ("thư ký chung") của KB: gói đóng góp -> đối chiếu -> gộp -> kiểm -> chấm điểm -> phiên bản -> xuất.

    run(packs) -> kết quả thuần (không đọc ghi file), dùng cho test và cho __main__.
"""
import collections

from kb_pipeline.core import finalize, run_core
from kb_pipeline.packs import validate_pack
from kb_pipeline.quality import apply_rules, blocking_checks
from kb_pipeline.schema import ACCEPT_POLICY, ROLE_GROUPS


def run(packs, role_groups=ROLE_GROUPS, policy=ACCEPT_POLICY):
    """Hàm thuần. Trả dict: nodes, edges, review, info, errors (lỗi chặn: có thì không được ghi)."""
    errors = [err for pack in packs for err in validate_pack(pack)]
    if errors:
        return {"nodes": [], "edges": [], "review": [], "info": {}, "resolved_by_alias": [], "errors": errors}
    kb, errors = run_core(packs, role_groups)
    nodes, edges = finalize(kb)
    edges, rule_review = apply_rules(nodes, edges, kb.sources, role_groups, policy)
    blocking = blocking_checks(nodes, edges, role_groups)
    errors += [f"{k}: {v}" for k, v in blocking.items()]
    return {"nodes": nodes, "edges": edges, "review": kb.review + rule_review, "info": dict(kb.info),
            "resolved_by_alias": kb.resolved_by_alias, "errors": errors}


def summarize(result):
    nodes, edges = result["nodes"], result["edges"]
    mapped = {e["src"] for e in edges if e["type"] == "MAPS_TO" and e["status"] != "rejected"}
    return {
        "nodes": dict(collections.Counter(n["label"] for n in nodes)),
        "edges": dict(collections.Counter(e["type"] for e in edges)),
        "node_status": dict(collections.Counter(n["status"] for n in nodes if n["label"] != "Source")),
        "edge_status": dict(collections.Counter(e["status"] for e in edges)),
        "accepted_by": {"nodes": dict(collections.Counter(n["accepted_by"] for n in nodes if n.get("accepted_by"))),
                        "edges": dict(collections.Counter(e["accepted_by"] for e in edges if e.get("accepted_by")))},
        "review": dict(collections.Counter(r["kind"] for r in result["review"])),
        "resolved_by_alias": len(result["resolved_by_alias"]),
        "info": result["info"],
        "job_titles_without_role_group": sum(1 for n in nodes if n["label"] == "JobTitle"
                                             and n["status"] != "rejected" and n["key"] not in mapped),
    }
