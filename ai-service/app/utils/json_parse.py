import json
import re


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
        return json_repair.loads(text)
    except Exception:
        pass

    raise ValueError("Model không trả về JSON hợp lệ")
