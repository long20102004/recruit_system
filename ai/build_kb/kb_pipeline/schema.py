"""Định dạng gói đóng góp (contribution pack) và luật chung của KB. Đặc tả đầy đủ ở docs/pack-format.md.

Một gói là một thư mục packs/<pack_id>/ gồm:
  manifest.json   {pack_id, kb_origin, priority, description, enabled, sources: [Source]}
  nodes.jsonl     khẳng định về thực thể: {label, name | ref, key?, aliases?, ambiguous_aliases?, sources?,
                  override?, <trường riêng của nhãn>}
  edges.jsonl     khẳng định về quan hệ: {type, src, dst, evidence: [{source_id, page, quote}], <thuộc tính riêng>}
  patches.jsonl   sửa KB đã gộp (tuỳ chọn): same_as / reject / ambiguous / set / drop_edge

Gói không cần biết KB hiện có gì: thực thể và đầu mút quan hệ gọi theo tên, pipeline tự đối chiếu.
"""
from shared.config import LEVEL_RANKS, ROLE_GROUPS  # noqa: F401  (dùng lại ở các module khác)

SKILL_TYPES = ("technology", "concept")
MAJOR_GROUPS = ("it", "related", "other")

# Trường riêng của từng nhãn -> kiểu hoặc tập giá trị hợp lệ
NODE_FIELDS = {
    "Skill": {"type": SKILL_TYPES},
    "Category": {"sibling_ok_suggest": bool, "sibling_ok": bool},
    "JobTitle": {"itviec_group": str},
    "Level": {"rank": int},
    "Major": {"group": MAJOR_GROUPS},
}
# Trường bắt buộc khi khẳng định tạo thực thể MỚI (thêm alias cho thực thể đã có thì không cần)
REQUIRED_NEW = {"Skill": ("type",), "Major": ("group",), "Level": ("rank",)}
NODE_RESERVED = {"label", "key", "name", "ref", "aliases", "ambiguous_aliases", "sources", "override"}

# Loại quan hệ -> (nhãn đầu, nhãn cuối)
EDGE_ENDS = {
    "PARENT_OF": ("Skill", "Skill"),
    "IN_CATEGORY": ("Skill", "Category"),
    "USED_IN": ("Skill", "RoleGroup"),
    "EVIDENCED_BY": ("Skill", "Source"),
    "MAPS_TO": ("JobTitle", "RoleGroup"),
    "NEAR": ("RoleGroup", "RoleGroup"),
}
EDGE_PROPS = {
    "PARENT_OF": {}, "IN_CATEGORY": {},
    "USED_IN": {"in_roadmap": bool, "node_kind": ("main", "sub", None)},
    "EVIDENCED_BY": {"page": int, "snippet": str},
    "MAPS_TO": {"method": str},
    "NEAR": {"m": float, "method": ("hypothesis", "computed"), "shared_skills": int},
}
EDGE_RESERVED = {"type", "src", "dst", "evidence", "sources"}
NODE_LABELS = tuple(NODE_FIELDS)

PATCH_OPS = {
    "same_as": ("label", "drop", "keep"),       # gộp drop vào keep
    "reject": ("label", "ref"),                 # status = rejected
    "ambiguous": ("label", "ref"),              # mọi alias (cả tên) thành alias dễ nhầm
    "set": ("label", "ref", "fields"),          # ghi đè trường
    "drop_edge": ("type", "src", "dst"),        # bỏ quan hệ
}

SOURCE_REQUIRED = ("source_id", "type", "title", "publisher", "trust")
TRUST_WEIGHT = {"high": 0.9, "medium": 0.6, "low": 0.3}     # Knowledge base.md mục 6, bước 3
GENERATED = "generated"                                    # Source.type của nguồn tự sinh

# Trạng thái: accepted, candidate, rejected (thiết kế) và review (pipeline: vi phạm luật, chờ người duyệt,
# không xuất cho module match)
STATUSES = ("accepted", "candidate", "review", "rejected")

# Chính sách nhận (Knowledge base.md mục 6, bước 2):
#   rule         đúng luật: ≥ 2 publisher độc lập hoặc 1 nguồn trust = high
#   provisional  TẠM THỜI (chốt 21/11/2026): mọi thực thể/quan hệ còn sống (không rejected, không review) đều
#                accepted. Cái không qua luật mang accepted_by = "provisional" để lọc lại khi quay về "rule".
ACCEPT_POLICIES = ("rule", "provisional")
ACCEPT_POLICY = "provisional"


def check_value(value, rule):
    """rule là kiểu (bool, int, float, str) hoặc tuple giá trị hợp lệ."""
    if isinstance(rule, tuple):
        return value in rule
    if rule is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if rule is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, rule)
