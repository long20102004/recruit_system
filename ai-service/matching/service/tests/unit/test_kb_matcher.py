import time

import pytest

from cvmatch.core.kb.snapshot import KBSnapshot
from cvmatch.core.text.normalize import normalize


def ids(matcher, text):
    return matcher.find_ids(normalize(text))


def test_longest_alias_first(matcher):
    assert ids(matcher, "Xây dựng API thanh toán bằng Spring Boot") == ["S0002"]
    assert ids(matcher, "App bằng React Native và React") == ["S0007", "S0006"]


def test_word_boundary(matcher):
    assert ids(matcher, "Lập trình JavaScript") == ["S0004"]
    assert "S0001" not in ids(matcher, "javascript developer")
    assert ids(matcher, "Phát triển ASP.NET Core") == ["S0018"]       # khong ra .NET
    assert ids(matcher, "dùng .NET 6") == ["S0017"]
    assert ids(matcher, "Java.") == ["S0001"]                          # cham cuoi cau


def test_special_chars(matcher):
    assert ids(matcher, "Thành thạo C++, C# và Node.js") == ["S0013", "S0014", "S0008"]
    assert ids(matcher, "Xây dựng pipeline CI/CD với Jenkins") == ["S0025", "S0026"]


def test_ambiguous_not_in_free_text_but_ok_as_list_item(matcher):
    assert ids(matcher, "Let's go to the market") == []
    assert ids(matcher, "dùng spring để viết") == []
    assert [m.skill_id for m in matcher.match_list_item("Go")] == ["S0011"]
    assert [m.skill_id for m in matcher.match_list_item(" R ")] == ["S0031"]
    assert ids(matcher, "Viết service bằng Golang") == ["S0011"]


def test_alias_to_canonical(matcher):
    assert ids(matcher, "Triển khai lên K8s") == ["S0020"]
    assert matcher.canonical_name("S0020") == "Kubernetes"


def test_concept_needs_long_alias(matcher):
    assert ids(matcher, "viết api cho app") == []                      # 'api' don le khong ra REST API
    assert ids(matcher, "thiết kế RESTful API") == ["S0024"]
    assert ids(matcher, "hiểu biết về microservices") == ["S0023"]


def test_list_item_with_several_skills_and_unknown(matcher):
    assert [m.skill_id for m in matcher.match_list_item("Java, Spring Boot")] == ["S0001", "S0002"]
    assert matcher.match_list_item("Figma") == []                      # -> unknown_skill o A5


def test_match_positions(matcher):
    t = normalize("Tối ưu truy vấn PostgreSQL")
    (m,) = matcher.find(t)
    assert t[m.start:m.end] == "postgresql" and m.skill_id == "S0015"


def test_duplicate_alias_rejected():
    rows = {
        "skill_ontology": [
            {"skill_id": "S1", "name": "A", "aliases": ["x"], "type": "technology"},
            {"skill_id": "S2", "name": "B", "aliases": ["X "], "type": "technology"},
        ],
        "role_title_map": [], "role_distance": [], "major_group": [], "ambiguous_aliases": [],
    }
    with pytest.raises(ValueError, match="hai ky nang"):
        KBSnapshot.from_rows({"ontology_version": "t"}, rows)


def test_matcher_speed(matcher):
    text = normalize("Xây dựng API thanh toán bằng Spring Boot, tối ưu truy vấn PostgreSQL, "
                     "triển khai Docker và Kubernetes, dùng Kafka cho microservices")
    t0 = time.perf_counter()
    for _ in range(5000):
        matcher.find(text)
    per = (time.perf_counter() - t0) / 5000
    print(f"\nSkillMatcher.find: {per * 1e6:.1f} us / cau (KB mini)")
    assert per < 2e-3


# ------------------------------------------------------------------ lookup


def test_split_title_and_role(lookup):
    assert lookup.split_title("Senior Java Developer") == (4, "java developer")
    assert lookup.parse_title("Senior Java Developer")[:2] == (4, "Backend")
    assert lookup.parse_title("Senior Backend Developer (Java)")[:2] == (4, "Backend")
    assert lookup.parse_title("Lập trình viên Java")[:2] == (None, "Backend")
    assert lookup.parse_title("Team Lead Frontend Developer")[:2] == (5, "Frontend")
    assert lookup.parse_title("Thực tập sinh Tester")[:2] == (0, "QA")
    assert lookup.parse_title("Nhân viên kinh doanh")[:2] == (None, None)


def test_major_group(lookup):
    assert lookup.major_group_of("Kỹ thuật phần mềm") == "it"
    assert lookup.major_group_of("Ngành Công nghệ thông tin (CLC)") == "it"
    assert lookup.major_group_of("Toán - Tin") == "related"
    assert lookup.major_group_of("Quan tri kinh doanh") == "other"    # khong dau
    assert lookup.major_group_of("Triết học") is None
