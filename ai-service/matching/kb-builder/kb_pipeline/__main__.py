"""Chạy thư ký chung trên mọi gói trong packs/.

    python -m kb_pipeline              gộp, kiểm, ghi out/ (JSONL, kb.cypher, diff, hàng đợi duyệt, phiên bản)
    python -m kb_pipeline --load       như trên rồi nạp Neo4j
    python -m kb_pipeline --dry-run    chỉ gộp và kiểm, in tóm tắt, không ghi gì
    python -m kb_pipeline --policy rule   nhận đúng luật mục 6 (mặc định tạm thời: provisional, nhận hết)

Có lỗi chặn (gói sai định dạng, alias trùng, quan hệ trỏ tới nút không có, vòng PARENT_OF) thì dừng, không ghi gì.
Những gì pipeline tự xử lý được (alias đã thuộc nút khác, giá trị mâu thuẫn, PARENT_OF sai luật...) thì ghi vào
out/review_queue.jsonl để người duyệt, KB vẫn được ghi.
"""
import argparse
import collections
import json
import pathlib

from kb_pipeline import run, summarize
from kb_pipeline.export import load_neo4j, to_cypher
from kb_pipeline.packs import PACKS_DIR, discover
from kb_pipeline.schema import ACCEPT_POLICIES, ACCEPT_POLICY, ROLE_GROUPS
from kb_pipeline.version import diff, make_version
from shared.common import read_jsonl, write_jsonl

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
FILES = {"nodes": OUT / "kb_nodes.jsonl", "edges": OUT / "kb_edges.jsonl", "checks": OUT / "kb_checks.json",
         "review": OUT / "review_queue.jsonl", "diff": OUT / "kb_diff.json", "cypher": OUT / "kb.cypher",
         "versions": OUT / "versions.jsonl"}


def read_or_empty(path):
    return read_jsonl(path) if path.exists() else []


def main(argv=None):
    ap = argparse.ArgumentParser(description="Thư ký chung: gộp mọi gói trong packs/ thành KB")
    ap.add_argument("--load", action="store_true", help="nạp Neo4j sau khi ghi out/")
    ap.add_argument("--dry-run", action="store_true", help="không ghi gì")
    ap.add_argument("--packs", default=str(PACKS_DIR), help="thư mục chứa gói")
    ap.add_argument("--policy", choices=ACCEPT_POLICIES, default=ACCEPT_POLICY,
                    help="rule: đúng luật mục 6; provisional: nhận hết (accepted_by = provisional)")
    args = ap.parse_args(argv)

    packs = discover(args.packs)
    if not packs:
        raise SystemExit(f"Không có gói nào trong {args.packs}: không gộp để tránh xoá KB đang có")
    print("Gói:", ", ".join(f"{p['manifest']['pack_id']} (ưu tiên {p['manifest']['priority']})" for p in packs))
    result = run(packs, ROLE_GROUPS, args.policy)
    if result["errors"]:
        raise SystemExit("KB có lỗi chặn, không ghi gì:\n" + "\n".join(str(e)[:2000] for e in result["errors"][:30]))
    nodes, edges = result["nodes"], result["edges"]
    summary = summarize(result)

    old_nodes, old_edges = read_or_empty(FILES["nodes"]), read_or_empty(FILES["edges"])
    changes = diff(old_nodes, old_edges, nodes, edges)
    history = read_or_empty(FILES["versions"])
    version, is_new = make_version(history, nodes, edges, packs, changes, old_nodes)
    summary["version"] = version["id"]
    summary["diff"] = changes["summary"]

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.dry_run:
        return
    write_jsonl(FILES["nodes"], nodes)
    write_jsonl(FILES["edges"], edges)
    write_jsonl(FILES["review"], result["review"])
    FILES["checks"].write_text(json.dumps({**summary, "resolved_by_alias": result["resolved_by_alias"]},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
    FILES["diff"].write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    if is_new:
        write_jsonl(FILES["versions"], [*history, version])
    FILES["cypher"].write_text(to_cypher(nodes, edges, version, ROLE_GROUPS,
                                         {"nodes": summary["nodes"], "edges": summary["edges"]}), encoding="utf-8")
    review = collections.Counter(r["kind"] for r in result["review"])
    print(f"Phiên bản {version['id']}{' (mới)' if is_new else ' (không đổi)'}. "
          f"Hàng đợi duyệt: {sum(review.values())} mục {dict(review)} ở {FILES['review']}")
    if args.load:
        counts, rels = load_neo4j(nodes, edges, version, ROLE_GROUPS, ROOT / ".env")
        print(f"Neo4j: {counts}\n{rels}")


if __name__ == "__main__":
    main()
