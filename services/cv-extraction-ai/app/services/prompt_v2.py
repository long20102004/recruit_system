"""Prompt v2: the single source of truth for training (feature 006) and serving.

The dataset builder renders every training sample with ``render_prompt`` and
``render_target``; serving with ``PROMPT_VERSION=v2`` calls ``render_prompt``.
Any change here requires rebuilding the dataset and retraining.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

SYSTEM_PROMPT = """Trích xuất CV thành MỘT object JSON đúng schema bên dưới.
- Chỉ dùng thông tin có trong CV. Chép nguyên văn: không dịch, không tóm tắt, không sửa chính tả, không thêm.
- Thiếu thông tin: trường đơn → null, danh sách → [].
- experience: công việc tại công ty/tổ chức (kể cả thực tập). description: mỗi bullet là một phần tử, chép nguyên văn.
- personal_projects: dự án cá nhân, đồ án, dự án trong mục Dự án. description: chép nguyên văn các ý mô tả, nối bằng dấu cách. tech_stack: chỉ công nghệ ghi cho chính dự án đó. team_size: số nguyên nếu CV ghi rõ.
- skills: kỹ năng trong mục Kỹ năng; mỗi kỹ năng một phần tử, bỏ tên nhóm (ví dụ "Backend:").
- Xếp theo tiêu đề mục trong CV: mục Chứng chỉ/Certifications → certificates; mục Giải thưởng/Thành tích/Achievements/Awards → honours (gồm cả học bổng); mục Ngôn ngữ/Languages → languages, với language = tên ngôn ngữ, note = trình độ hoặc điểm.
- Ngày tháng giữ đúng như CV; start_year/end_year là số nguyên.
Schema:
{"personal_info":{"full_name":null,"email":null,"phone":null,"github_url":null},"objective":null,"education":[{"school":null,"major":null,"start_year":null,"end_year":null,"gpa":null}],"experience":[{"company":null,"job_title":null,"start_date":null,"end_date":null,"description":[]}],"personal_projects":[{"name":null,"role":null,"team_size":null,"start_date":null,"end_date":null,"github_url":null,"description":null,"tech_stack":[]}],"skills":[],"certificates":[],"honours":[],"languages":[{"language":null,"note":null}]}"""

HINTS_HEADER = "Kỹ năng trong KB xuất hiện trong CV (chỉ để tham khảo chính tả, không tự thêm):"

# Qwen3 non-thinking turn: the empty think block is part of the prompt, not of the target.
ASSISTANT_PREFIX = "<|im_start|>assistant\n<think>\n\n</think>\n\n"
END_OF_TURN = "<|im_end|>"

# Key order of the target JSON (matches the silver labels).
TOP_KEYS = ("personal_info", "objective", "education", "experience", "personal_projects",
            "skills", "certificates", "honours", "languages")


def render_prompt(cv_text: str, candidate_skills: Iterable[str] | None = None) -> str:
    """ChatML prompt ending right where the model starts writing the JSON."""
    user = cv_text.strip()
    hints = [s for s in (candidate_skills or []) if s]
    if hints:
        user += "\n\n" + HINTS_HEADER + " " + ", ".join(hints)
    return (f"<|im_start|>system\n{SYSTEM_PROMPT}{END_OF_TURN}\n"
            f"<|im_start|>user\n{user}{END_OF_TURN}\n"
            f"{ASSISTANT_PREFIX}")


def render_target(profile: dict[str, Any]) -> str:
    """Compact JSON of a full-schema profile plus the end-of-turn token."""
    ordered = {k: profile[k] for k in TOP_KEYS if k in profile}
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":")) + END_OF_TURN
