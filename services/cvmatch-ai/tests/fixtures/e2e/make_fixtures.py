"""Sinh bo fixture T13: 36 CV tong hop da vai tro + 3 JD (du lieu GIA, khong phai CV that).

Chay lai: `python tests/fixtures/e2e/make_fixtures.py` (ghi de cv/*.json, jd/*.json). Tat dinh.
Ten ky nang lay tu KB mini (tests/fixtures/kb_mini) de chay duoc ca voi KB mini lan KB that.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

# vai tro -> (chuc danh, ky nang, cac gach mo ta)
ROLES = {
    "java": ("Java Developer", ["Java", "Spring Boot", "PostgreSQL", "Kafka", "Docker", "Redis"], [
        "Thiết kế và phát triển REST API cho hệ thống thanh toán bằng Spring Boot",
        "Tối ưu hiệu năng truy vấn cơ sở dữ liệu PostgreSQL, giảm 40% thời gian phản hồi",
        "Xây dựng luồng xử lý sự kiện bất đồng bộ với Kafka cho đơn hàng",
        "Viết unit test và integration test cho các service backend",
        "Triển khai microservices lên Docker và Kubernetes",
        "Thiết kế cache Redis cho các API có tải cao",
    ]),
    "python": ("Python Developer", ["Python", "Django", "MySQL", "Redis", "Docker"], [
        "Phát triển API quản lý đơn hàng bằng Django REST framework",
        "Tối ưu truy vấn MySQL cho các báo cáo doanh thu hàng ngày",
        "Viết tác vụ nền xử lý dữ liệu với Celery và Redis",
        "Tích hợp cổng thanh toán và dịch vụ gửi email cho khách hàng",
    ]),
    "frontend": ("Frontend Developer", ["JavaScript", "TypeScript", "React", "Vue.js", "Git"], [
        "Xây dựng giao diện trang quản trị bằng React và TypeScript",
        "Tối ưu tốc độ tải trang, cải thiện điểm Lighthouse từ 60 lên 90",
        "Phát triển thư viện component dùng chung cho nhiều dự án",
        "Kết nối giao diện với REST API và xử lý trạng thái bằng Redux",
    ]),
    "fullstack": ("Fullstack Developer", ["JavaScript", "Node.js", "React", "PostgreSQL", "Docker"], [
        "Phát triển API bằng Node.js và giao diện quản trị bằng React",
        "Thiết kế cơ sở dữ liệu PostgreSQL cho hệ thống đặt lịch",
        "Đóng gói ứng dụng bằng Docker và cấu hình CI/CD với Jenkins",
        "Xây dựng tính năng thông báo thời gian thực bằng WebSocket",
    ]),
    "mobile": ("Android Developer", ["Kotlin", "Java", "Git", "REST API"], [
        "Phát triển ứng dụng Android bán hàng bằng Kotlin",
        "Tích hợp thanh toán trong ứng dụng và đẩy thông báo",
        "Tối ưu bộ nhớ và thời gian khởi động ứng dụng di động",
    ]),
    "data": ("Data Engineer", ["Python", "SQL", "Kafka", "AWS", "PostgreSQL"], [
        "Xây dựng pipeline ETL xử lý hàng triệu bản ghi mỗi ngày bằng Python",
        "Thiết kế kho dữ liệu và các bảng tổng hợp phục vụ báo cáo",
        "Xử lý dữ liệu luồng thời gian thực với Kafka",
        "Triển khai các job xử lý dữ liệu trên AWS",
    ]),
    "devops": ("DevOps Engineer", ["Docker", "Kubernetes", "AWS", "Jenkins", "CI/CD", "Git"], [
        "Vận hành cụm Kubernetes cho hơn 50 microservices",
        "Xây dựng pipeline CI/CD bằng Jenkins cho toàn bộ dự án",
        "Giám sát hệ thống và cảnh báo sự cố bằng Prometheus và Grafana",
        "Tự động hoá hạ tầng AWS bằng Terraform",
    ]),
    "qa": ("QA Engineer", ["Java", "SQL", "Git"], [
        "Viết kịch bản kiểm thử tự động cho ứng dụng web bằng Selenium",
        "Kiểm thử API và kiểm tra dữ liệu trong cơ sở dữ liệu bằng SQL",
        "Báo cáo lỗi và theo dõi chất lượng phát hành mỗi sprint",
    ]),
    "designer": ("Graphic Designer", ["Photoshop"], [
        "Thiết kế banner quảng cáo và ấn phẩm truyền thông",
        "Chỉnh sửa ảnh sản phẩm bằng Photoshop cho trang thương mại điện tử",
    ]),
}
LEVELS = ["Fresher", "Junior", "", "Senior"]
LOCATIONS = ["TP.HCM", "Hà Nội", "Đà Nẵng"]
MAJORS = ["Kỹ thuật phần mềm", "Khoa học máy tính", "Hệ thống thông tin", "Thiết kế đồ hoạ"]

NOACC = {"java": ["Thiet ke va phat trien REST API cho he thong thanh toan bang Spring Boot",
                  "Toi uu truy van co so du lieu PostgreSQL cho bao cao"]}


def make_cv(i: int, role: str, rng: random.Random, variant: str = "") -> dict:
    title, skills, bullets = ROLES[role]
    level = LEVELS[i % len(LEVELS)]
    start_year = {"Fresher": 2025, "Junior": 2023, "": 2021, "Senior": 2017}[level]
    n_b = rng.randint(2, len(bullets))
    desc: list[str] | str = rng.sample(bullets, n_b)
    if variant == "paragraph":
        desc = ". ".join(desc) + "."
    elif variant == "no_bullets":
        desc = []
    elif variant == "noacc":
        desc = NOACC["java"]
    exp = [{"title": f"{level} {title}".strip(), "company": f"Công ty {chr(65 + i % 26)}",
            "start": f"{start_year}-0{1 + i % 9}", "end": None, "is_current": True,
            "description": desc, "technologies": rng.sample(skills, min(3, len(skills)))}]
    if level in ("", "Senior"):
        prev = rng.choice([r for r in ROLES if r != "designer"]) if variant == "switch" else role
        ptitle, _, pbul = ROLES[prev]
        exp.append({"title": ptitle, "company": f"Công ty {chr(75 + i % 10)}", "start": f"{start_year - 3}-03",
                    "end": f"{start_year - 1}-12", "description": rng.sample(pbul, 2)})
    if variant == "bad_dates":
        exp[0]["start"] = "mùa xuân năm ngoái"
    cv = {
        "full_name": f"Ứng viên {i:02d}",
        "email": f"ungvien{i:02d}@example.com",
        "phone": f"09{i:08d}",
        "location": LOCATIONS[i % len(LOCATIONS)],
        "summary": f"{title} {'nhiều năm' if level == 'Senior' else ''} kinh nghiệm".replace("  ", " "),
        "skills": skills[: rng.randint(min(2, len(skills)), len(skills))],
        "experiences": exp,
        "projects": [],
        "education": [{"school": "Đại học Bách khoa", "major": MAJORS[3 if role == "designer" else i % 3],
                       "end": str(start_year - 1 if level != "Fresher" else 2024)}],
        "certificates": [], "languages": ["Tiếng Anh"],
    }
    if variant == "project":
        cv["projects"] = [{"name": "Dự án cá nhân", "kind": "personal",
                           "description": [rng.choice(bullets)], "technologies": skills[:2]}]
    return cv


JDS = [
    {"jd_id": "E2E-JAVA", "title": "Senior Backend Developer (Java)", "location": "TP.HCM", "work_mode": "hybrid",
     "min_years": 4, "level": "Senior",
     "skills": [{"name": "Java", "required": True, "importance": "core"},
                {"name": "Spring Boot", "required": True, "importance": "core"},
                {"name": "PostgreSQL", "required": True, "importance": "medium"},
                {"name": "Kafka", "required": False, "importance": "minor"}],
     "requirements": ["Tối thiểu 4 năm kinh nghiệm phát triển backend", "Hiểu biết về microservices"],
     "responsibilities": ["Thiết kế và phát triển API cho hệ thống thanh toán",
                          "Tối ưu hiệu năng truy vấn cơ sở dữ liệu",
                          "Xây dựng luồng xử lý sự kiện bất đồng bộ cho đơn hàng",
                          "Tham gia các buổi họp của team"],
     "benefits": ["Lương tháng 13"], "status": "open"},
    {"jd_id": "E2E-FE", "title": "Frontend Developer (React)", "location": "Hà Nội", "min_years": 2,
     "skills": [{"name": "React", "required": True, "importance": "core"},
                {"name": "TypeScript", "required": True, "importance": "medium"},
                {"name": "JavaScript", "required": True, "importance": "core"}],
     "requirements": ["Có kinh nghiệm làm việc với REST API"],
     "responsibilities": ["Xây dựng giao diện quản trị bằng React",
                          "Tối ưu tốc độ tải trang và trải nghiệm người dùng",
                          "Phát triển các component dùng chung"],
     "status": "open"},
    {"jd_id": "E2E-DATA", "title": "Data Engineer", "location": "TP.HCM", "work_mode": "remote", "min_years": 3,
     "skills": ["Python", "SQL", "Kafka", "AWS"],          # khong co required/importance -> w_imp = 1
     "requirements": ["Kinh nghiệm xây dựng pipeline dữ liệu"],
     "responsibilities": ["Xây dựng pipeline ETL xử lý dữ liệu lớn",
                          "Xử lý dữ liệu luồng thời gian thực",
                          "Thiết kế kho dữ liệu phục vụ báo cáo"],
     "status": "open"},
]


def main() -> None:
    rng = random.Random(13)
    plan = (["java"] * 7 + ["python"] * 4 + ["frontend"] * 5 + ["fullstack"] * 3 + ["mobile"] * 3 + ["data"] * 4
            + ["devops"] * 3 + ["qa"] * 3 + ["designer"] * 2)
    variants = {2: "paragraph", 5: "no_bullets", 6: "noacc", 9: "switch", 13: "project", 20: "bad_dates",
                27: "switch", 30: "project"}
    for d in ("cv", "jd"):
        (HERE / d).mkdir(exist_ok=True)
        for f in (HERE / d).glob("*.json"):
            f.unlink()
    for i, role in enumerate(plan):
        cv = make_cv(i, role, rng, variants.get(i, ""))
        (HERE / "cv" / f"cv_{i:02d}_{role}.json").write_text(json.dumps(cv, ensure_ascii=False, indent=1),
                                                            encoding="utf-8")
    for jd in JDS:
        (HERE / "jd" / f"{jd['jd_id'].lower()}.json").write_text(json.dumps(jd, ensure_ascii=False, indent=1),
                                                                 encoding="utf-8")
    print(f"{len(plan)} CV, {len(JDS)} JD -> {HERE}")


if __name__ == "__main__":
    main()
