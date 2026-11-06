"""Unit tests cho ``app.utils.json_parse.extract_json``.

Chỉ dùng dữ liệu CV tổng hợp (synthetic), không có PII thật.

Các tình huống output thực tế của model:
- JSON thuần;
- JSON bọc trong markdown fence ```json ... ```;
- JSON nằm trước thẻ ``</think>``, rác nằm sau thẻ;
- Text có tiền tố rác rồi mới tới object JSON;
- JSON lỗi nhẹ (dấu phẩy thừa) được ``json_repair`` sửa.
"""

import json

from app.utils.json_parse import extract_json


def _synthetic_profile() -> dict:
    """CandidateProfile tổng hợp, không chứa dữ liệu cá nhân thật."""
    return {
        "personal_info": {
            "full_name": "Nguyen Van Synthetic",
            "email": "synthetic.candidate@example.test",
            "phone": "0900000002",
            "github_url": "https://example.test/synthetic",
        },
        "objective": "Thực tập sinh Backend",
        "education": [
            {
                "school": "Học viện Synthetic",
                "major": "Công nghệ thông tin",
                "start_year": 2021,
                "end_year": 2025,
            }
        ],
        "experience": [],
        "personal_projects": [],
        "skills": ["Python", "SQL"],
        "certificates": [],
        "honours": [],
        "languages": ["Tiếng Việt"],
    }


def test_plain_json_returns_same_dict():
    profile = _synthetic_profile()
    raw = json.dumps(profile, ensure_ascii=False)

    assert extract_json(raw) == profile


def test_json_wrapped_in_markdown_fence():
    profile = _synthetic_profile()
    raw = "```json\n" + json.dumps(profile, ensure_ascii=False) + "\n```"

    assert extract_json(raw) == profile


def test_json_before_think_tag_and_garbage_after():
    """Phần trước ``</think>`` là JSON; rác sau thẻ bị cắt bỏ."""
    profile = _synthetic_profile()
    raw = (
        json.dumps(profile, ensure_ascii=False)
        + "\n</think>\n\n"
        + "Đây là phần rác sau thẻ, ví dụ {broken json: không hợp lệ"
    )

    assert extract_json(raw) == profile


def test_junk_prefix_before_json_object():
    profile = _synthetic_profile()
    raw = (
        "Dưới đây là kết quả trích xuất CV:\n\n"
        + json.dumps(profile, ensure_ascii=False)
        + "\n\nHết kết quả."
    )

    assert extract_json(raw) == profile


def test_trailing_commas_repaired_by_json_repair():
    """JSON lỗi nhẹ do dấu phẩy thừa vẫn được ``json_repair`` sửa."""
    raw = (
        "{"
        '"personal_info": {'
        '"full_name": "Nguyen Van Synthetic",'
        '"email": "synthetic.candidate@example.test",'
        "},"
        '"skills": ["Python", "SQL",],'
        "}"
    )

    result = extract_json(raw)

    assert result["personal_info"]["full_name"] == "Nguyen Van Synthetic"
    assert result["personal_info"]["email"] == "synthetic.candidate@example.test"
    assert result["skills"] == ["Python", "SQL"]


def test_premature_close_fragments_are_merged():
    """Model closed the top-level object early: '{"personal_info":{...}}},{"education":[...]}'."""
    text = ('{"personal_info":{"full_name":"Nguyen Van Synthetic"},"objective":null}},'
            '{"education":[{"school":"Học viện Synthetic"}],"skills":["Python"]}')
    data = extract_json(text)
    assert data["personal_info"]["full_name"] == "Nguyen Van Synthetic"
    assert data["education"][0]["school"] == "Học viện Synthetic"
    assert data["skills"] == ["Python"]


def test_orphan_projects_go_back_to_their_list():
    text = ('{"personal_info":{"full_name":"Nguyen Van Synthetic"},"personal_projects":[{"name":"P1","tech_stack":["Java"]}]}]},'
            '{"name":"P2","tech_stack":["Go"]},{"name":"P3","description":["Synthetic bullet"]},["stray", "list"]')
    data = extract_json(text)
    assert [p["name"] for p in data["personal_projects"]] == ["P1", "P2", "P3"]

