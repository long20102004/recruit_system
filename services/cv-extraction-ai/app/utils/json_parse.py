import json
import re

TOP_KEYS = ("personal_info", "objective", "education", "experience", "personal_projects",
            "skills", "certificates", "honours", "languages")
# A fragment with these keys is a list item that a premature "}" pushed out of its list.
_ITEM_LIST = (("company", "experience"), ("school", "education"), ("tech_stack", "personal_projects"),
              ("name", "personal_projects"))


def merge_fragments(parts) -> dict | None:
    """Rebuild one profile from the fragments json_repair returns when the model closed the
    top-level object too early ('{...}},{...}'): later top-level keys fill/extend the first
    object, orphan list items go back to their list, anything ambiguous is dropped."""
    if isinstance(parts, dict):
        return parts
    if not isinstance(parts, list):
        return None
    base = None
    for part in parts:
        if not isinstance(part, dict):
            continue
        if base is None:
            base = dict(part)
            continue
        top = [k for k in part if k in TOP_KEYS]
        if top:
            for k in top:
                v = part[k]
                if isinstance(base.get(k), list) and isinstance(v, list):
                    base[k] = base[k] + v
                elif not base.get(k):
                    base[k] = v
            continue
        target = next((lst for key, lst in _ITEM_LIST if key in part), None)
        if target:
            current = base.get(target)
            base[target] = (current if isinstance(current, list) else []) + [part]
    return base


def extract_json(text: str) -> dict:
    # 1. Nếu có thẻ </think>, cắt bỏ toàn bộ phần rác phía sau nó
    if "</think>" in text:
        text = text.split("</think>")[0].strip()

    # 2. Xóa các markdown block ```json ... ```
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # 3. Thử parse trực tiếp
    try:
        return json.loads(text)
    except Exception:
        pass

    # 4. Tìm khối { ... } đầu tiên hợp lệ nhất
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 5. Fallback qua json_repair nếu có thư viện
    try:
        import json_repair
        repaired = merge_fragments(json_repair.loads(text))
        if repaired is not None:
            return repaired
    except Exception:
        pass

    raise ValueError("Model không trả về JSON hợp lệ")
