"""Sinh CV dang DAU RA Module 1 (du lieu GIA, khong phai CV that) cho test adapter (I03).

Chay lai: python tests/fixtures/module1/make_fixtures.py. Neu co ma nguon `services/cv-extraction-ai`, moi CV duoc
dua qua `normalize_profile` cua Module 1 de dung y hinh dang that (du truong, kieu, bo truong la).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXTRACTION = HERE.parents[4] / "services" / "cv-extraction-ai"

KG = {"skills_normalized": [{"id": 1, "name": "Java", "surface": "java"}],
      "implied_skills": [{"id": 9, "name": "JVM", "category": "Runtime", "via": [{"from": "Java", "rel": "REQUIRES"}]}],
      "skills_detected": ["Docker"], "related_skills": [{"name": "Kotlin", "weight": 0.4}], "flags": ["kg_ok"]}

CVS = {
    "m1_backend_java": {
        "personal_info": {"full_name": "Nguyễn Văn Giả", "email": "gia.backend@example.test", "phone": "0900000001",
                          "github_url": "https://github.com/example-gia"},
        "objective": "Lập trình viên backend 4 năm kinh nghiệm Java, Spring Boot, muốn phát triển hệ thống lớn.",
        "education": [{"school": "Đại học Bách khoa Hà Nội", "major": "Khoa học máy tính", "start_year": "2015",
                       "end_year": "2019", "gpa": "3.2/4"}],
        "experience": [
            {"company": "Công ty Phần mềm A", "job_title": "Backend Developer", "start_date": "03/2022",
             "end_date": None, "description": ["Thiết kế REST API bằng Spring Boot cho hệ thống thanh toán",
                                               "Tối ưu truy vấn PostgreSQL, giảm 40% thời gian phản hồi",
                                               "Triển khai dịch vụ bằng Docker và Kubernetes"]},
            {"company": "Công ty B", "job_title": "Java Developer", "start_date": "T7/2019", "end_date": "02/2022",
             "description": ["Phát triển module quản lý đơn hàng bằng Java, Hibernate", "Viết unit test với JUnit"]},
        ],
        "personal_projects": [{"name": "Hệ thống đặt vé", "role": "Backend", "team_size": "4", "start_date": "2021",
                               "end_date": "2021", "github_url": None,
                               "description": ["Xây dựng API đặt vé, xử lý đồng thời bằng Redis lock"],
                               "tech_stack": ["Java", "Spring Boot", "Redis", "MySQL"]}],
        "skills": ["Java", "Spring Boot", "PostgreSQL", "Docker", "Kubernetes", "Redis", "Git"],
        "certificates": ["Oracle Certified Professional Java SE 11"],
        "honours": [], "languages": [{"language": "Tiếng Anh", "note": "TOEIC 750"}],
        **KG,
    },
    "m1_frontend_english": {
        "personal_info": {"full_name": "Fake Person", "email": "fake.fe@example.test", "phone": None, "github_url": None},
        "objective": "Frontend engineer focused on React and TypeScript.",
        "education": [{"school": "University of Information Technology", "major": "Software Engineering",
                       "start_year": "2018", "end_year": "2022", "gpa": None}],
        "experience": [{"company": "Startup C", "job_title": "Frontend Developer", "start_date": "Mar 2022",
                        "end_date": "Present", "description": ["Built dashboard UI with React, Redux and TypeScript",
                                                               "Improved Lighthouse score from 60 to 92"]}],
        "personal_projects": [], "skills": ["ReactJS", "TypeScript", "HTML", "CSS", "Tailwind"],
        "certificates": [], "honours": ["Top 10 Hackathon 2021"], "languages": [{"language": "English", "note": "IELTS 7.0"}],
    },
    "m1_student_phone_only": {
        "personal_info": {"full_name": "Trần Thị Mẫu", "email": None, "phone": "+84 912 000 002", "github_url": None},
        "objective": "Sinh viên năm cuối tìm vị trí thực tập Data.",
        "education": [{"school": "Đại học Kinh tế Quốc dân", "major": "Hệ thống thông tin quản lý",
                       "start_year": "2022", "end_year": None, "gpa": "3.5"}],
        "experience": [],
        "personal_projects": [{"name": "Phân tích doanh số", "role": None, "team_size": None, "start_date": "09/2025",
                               "end_date": "12/2025", "github_url": None,
                               "description": ["Làm sạch dữ liệu bằng Pandas, vẽ biểu đồ bằng Power BI"],
                               "tech_stack": ["Python", "Pandas", "Power BI"]}],
        "skills": ["Python", "SQL", "Excel"], "certificates": [], "honours": [], "languages": [],
    },
    "m1_empty_personal": {
        "personal_info": {"full_name": None, "email": None, "phone": None, "github_url": None},
        "objective": None, "education": [],
        "experience": [{"company": "Công ty D", "job_title": "Tester", "start_date": None, "end_date": None,
                        "description": ["Kiểm thử thủ công ứng dụng di động"]}],
        "personal_projects": [], "skills": ["Manual Testing"], "certificates": [], "honours": [], "languages": [],
    },
    "m1_devops_bad_date": {
        "personal_info": {"full_name": "Lê Giả Lập", "email": "LE.GIA@Example.Test ", "phone": "0900000003", "github_url": None},
        "objective": "Kỹ sư DevOps.",
        "education": [{"school": "Học viện Công nghệ Bưu chính Viễn thông", "major": "Mạng máy tính",
                       "start_year": "2014", "end_year": "2018", "gpa": None}],
        "experience": [{"company": "Công ty E", "job_title": "DevOps Engineer", "start_date": "giữa năm 2020",
                        "end_date": "2023", "description": ["Xây dựng CI/CD bằng Jenkins và GitLab CI",
                                                            "Quản lý hạ tầng AWS bằng Terraform"]}],
        "personal_projects": [], "skills": ["AWS", "Terraform", "Jenkins", "Linux"], "certificates": ["AWS SAA"],
        "honours": [], "languages": [],
    },
}


def normalize(cv):
    if not (EXTRACTION / "app" / "postprocess" / "schema.py").exists():
        return cv
    sys.path.insert(0, str(EXTRACTION))
    from app.postprocess.schema import normalize_profile  # noqa: PLC0415

    kg = {k: cv[k] for k in KG if k in cv}
    out = normalize_profile({k: v for k, v in cv.items() if k not in KG})
    return {**out, **kg}


if __name__ == "__main__":
    for name, cv in CVS.items():
        (HERE / f"{name}.json").write_text(json.dumps(normalize(cv), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(CVS)} CV -> {HERE}")
