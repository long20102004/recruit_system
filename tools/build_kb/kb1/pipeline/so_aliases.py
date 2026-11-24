"""Thêm alias từ tag synonyms của Stack Overflow vào Skill. Bước 5 gọi trước khi ghi kb1_nodes.jsonl.

Mặc định loại: tag chỉ được nhận khi cùng tên với tag đích (khác cách viết, số nhiều) hoặc đã duyệt tay
trong config, vì synonym của SO thường là khái niệm hẹp hơn ("css-border-radius" -> css).
"""
import collections
import csv
import re

from shared.common import norm
from kb1.pipeline.config import AMBIGUOUS_ALIASES, SO_AMBIGUOUS, SO_BRIDGE, SO_FILLER_TOKENS, SO_KEEP

VERSION = r"v?\d+(?:\.\d+)*(?:\.x)?"
VERSION_SUFFIX = rf"[-.]?{VERSION}$"
VERSION_TOKEN = rf"(?:^|-)(?:{VERSION}|vnext)(?:-|$)"
REPORT_FIELDS = ["synonym", "target", "skill", "decision", "reason", "added"]


def is_version(tag, target):
    """python-3.11, angular4, pandas-2.x; không tính ec2, k8s, oauth2 -> oauth-2.0."""
    if re.search(VERSION_TOKEN, tag):
        return True
    base = re.sub(VERSION_SUFFIX, "", tag)
    target_has_version = re.sub(VERSION_SUFFIX, "", target) != target
    return bool(base) and base != tag and not target_has_version and (
        base.startswith(target) or target.startswith(base))


def core_name(tag):
    """Bỏ từ đệm, dấu phân cách, đuôi js: apache-solr -> solr, vue-js -> vue."""
    tokens = [t for t in re.split(r"[-.\s]+", tag) if t and t not in SO_FILLER_TOKENS]
    return re.sub(r"(?<=.)js$", "", "".join(tokens))


def stem(name):
    """Bỏ đuôi số nhiều và -ing: unittests, unittesting -> unittest."""
    return re.sub(r"(?<=...)ing$", "", re.sub(r"(?<=...)(?<!s)s$", "", name))


def classify(tag, target, skill_key):
    """Trả (decision, reason), decision là alias, ambiguous hoặc drop."""
    if tag in SO_AMBIGUOUS or tag in AMBIGUOUS_ALIASES:
        return "ambiguous", "từ thường hoặc quá ngắn"
    if tag in SO_KEEP or tag == target:
        return "alias", "đã duyệt tay"
    if is_version(tag, target):
        return "drop", "phiên bản"
    if tag.startswith(".") and not target.startswith("."):
        return "drop", "đuôi file"
    names = {core_name(target), core_name(skill_key)}
    if core_name(tag) in names:
        return "alias", "cùng tên, khác cách viết"
    # Chỉ nhận với tên ghép: "unit-tests" có ích, còn "points" -> point chỉ là từ thường
    if "-" in tag and stem(core_name(tag)) in {stem(n) for n in names}:
        return "alias", "cùng tên, số nhiều hoặc -ing"
    return "drop", "không chắc cùng nghĩa"


def load_synonyms(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(report)


def apply_so_aliases(kb_nodes, rows):
    """Thêm alias vào kb_nodes tại chỗ. Trả (báo cáo từng tag khớp KB, số dòng theo quyết định)."""
    skills = {n["key"]: n for n in kb_nodes if n["label"] == "Skill"}
    owner = {}
    for node in skills.values():
        for alias in [node["key"], *node["aliases"], *node["ambiguous_aliases"]]:
            owner[alias] = node["key"]

    def skill_of(target):
        bridged = SO_BRIDGE.get(target)
        if bridged in skills:
            return bridged
        return owner.get(target) or owner.get(target.replace("-", " "))

    def add(tag, target, skill_key):
        forms = sorted({tag, tag.replace("-", " ")})
        others = sorted({owner[f] for f in forms if f in owner} - {skill_key})
        new_forms = [f for f in forms if f not in owner]
        added = []
        if others:         # không thêm dạng nào, để một alias không chia cho hai kỹ năng
            decision, reason = "conflict", f"đã thuộc skill {others[0]}, xem có nên gộp không"
        elif not new_forms:
            decision, reason = "exists", "đã có"
        else:
            decision, reason = classify(tag, target, skill_key)
            if decision != "drop":
                field = "aliases" if decision == "alias" else "ambiguous_aliases"
                skills[skill_key][field] = sorted({*skills[skill_key][field], *new_forms})
                owner.update(dict.fromkeys(new_forms, skill_key))
                added = new_forms
        return {"synonym": tag, "target": target, "skill": skill_key, "decision": decision,
                "reason": reason, "added": "|".join(added)}

    report, counts = [], collections.Counter()
    for row in rows:
        tag, target = norm(row["synonym"]), norm(row["target"])
        skill_key = skill_of(target)
        if not skill_key:
            counts["not_in_kb"] += 1
            continue
        report.append(add(tag, target, skill_key))
        counts[report[-1]["decision"]] += 1
    for target, skill_key in SO_BRIDGE.items():      # tên tag đích của SO cũng là một tên gọi của kỹ năng
        if skill_key in skills:
            report.append(add(target, target, skill_key))
            counts[report[-1]["decision"]] += 1
    return report, dict(counts)
