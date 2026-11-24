"""Prompt v3: single source of truth for training and serving (PROMPT_VERSION=v4).

Serving v4 uses this prompt with the layout-aware model; the system prompt keeps the label
conventions found on real CVs: spoken languages only, skills from every sub-group without group
labels, company name only, content of two-column PDFs put back together.
Any change here requires rebuilding the dataset and retraining.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

# Qwen3 non-thinking turn: the empty think block is part of the prompt, not of the target.
ASSISTANT_PREFIX = "<|im_start|>assistant\n<think>\n\n</think>\n\n"
END_OF_TURN = "<|im_end|>"

# Key order of the target JSON (matches the silver labels).
TOP_KEYS = ("personal_info", "objective", "education", "experience", "personal_projects",
            "skills", "certificates", "honours", "languages")


SYSTEM_PROMPT = """Trích xuất CV thành MỘT object JSON đúng schema bên dưới.
- Chỉ dùng thông tin có trong CV. Chép nguyên văn: không dịch, không tóm tắt, không sửa chính tả, không thêm. Thiếu: trường đơn → null, danh sách → [].
- CV có thể là PDF hai cột nên các dòng bị xen kẽ: ghép đúng nội dung của từng mục, không bỏ sót.
- experience: công việc tại công ty/tổ chức (kể cả thực tập). company: CHỈ tên tổ chức, không kèm địa điểm, ngày hay chức danh. end_date = null nếu đang làm (Present/Now/Hiện tại). description: mỗi bullet một phần tử.
- personal_projects: dự án cá nhân, đồ án, dự án trong mục Dự án. description: các ý mô tả, mỗi ý một phần tử. tech_stack: từng công nghệ của chính dự án đó, bỏ tên nhóm. team_size: số nguyên nếu CV ghi rõ.
- skills: mọi kỹ năng trong mục Kỹ năng, gồm TẤT CẢ các nhóm con (Languages, Frameworks, Database, Tools, Soft skills...); mỗi kỹ năng một phần tử, bỏ tên nhóm. Ngôn ngữ lập trình (Java, Python, C#...) luôn thuộc skills.
- languages: CHỈ ngoại ngữ / ngôn ngữ tự nhiên (English, Tiếng Anh, Japanese, Vietnamese...); language = tên, note = trình độ hoặc điểm. Không bao giờ đưa ngôn ngữ lập trình vào languages.
- certificates: mục Chứng chỉ/Certifications. honours: mục Giải thưởng/Thành tích/Achievements/Awards (gồm học bổng).
- start_year, end_year, team_size là số nguyên.
Schema:
{"personal_info":{"full_name":null,"email":null,"phone":null,"github_url":null},"objective":null,"education":[{"school":null,"major":null,"start_year":null,"end_year":null,"gpa":null}],"experience":[{"company":null,"job_title":null,"start_date":null,"end_date":null,"description":[]}],"personal_projects":[{"name":null,"role":null,"team_size":null,"start_date":null,"end_date":null,"github_url":null,"description":[],"tech_stack":[]}],"skills":[],"certificates":[],"honours":[],"languages":[{"language":null,"note":null}]}"""


def render_prompt(cv_text: str, candidate_skills: Iterable[str] | None = None) -> str:
    """ChatML prompt ending where the model starts writing the JSON (hints unused in v3)."""
    return (f"<|im_start|>system\n{SYSTEM_PROMPT}{END_OF_TURN}\n"
            f"<|im_start|>user\n{cv_text.strip()}{END_OF_TURN}\n"
            f"{ASSISTANT_PREFIX}")


def render_target(profile: dict[str, Any]) -> str:
    """Compact JSON of a full-schema profile plus the end-of-turn token."""
    ordered = {k: profile[k] for k in TOP_KEYS if k in profile}
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":")) + END_OF_TURN
