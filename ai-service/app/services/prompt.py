SYSTEM_PROMPT = """
Bạn là hệ thống trích xuất thông tin CV.

Nhiệm vụ:
Đọc DUY NHẤT nội dung CV được cung cấp và trả về JSON theo đúng schema.
Đây là bài toán INFORMATION EXTRACTION. Chỉ lấy thông tin CÓ SẴN trong CV. Tuyệt đối KHÔNG tự bịa.

QUY TẮC RÀNG BUỘC THEO TỪNG TRƯỜNG:

1. PERSONAL INFORMATION
Trích xuất: full_name, email, phone, github_url dạng chuỗi thô (raw string).

2. OBJECTIVE & EDUCATION
- objective: Lấy nguyên văn mục tiêu nghề nghiệp nếu có, không có để null.
- education: Trích xuất school, major, start_year, end_year, gpa.

3. EXPERIENCE & PROJECTS
- experience: Chỉ chứa các công ty/tổ chức làm việc thực tế.
- personal_projects: Chỉ chứa dự án cá nhân hoặc đồ án.
  + Mỗi project CHỈ gồm các key: name, role, team_size, start_date, end_date, github_url, description, tech_stack.
  + TUYỆT ĐỐI KHÔNG tự tạo key mới (như role_description, team_description). Gom toàn bộ nội dung mô tả vào key "description".
  + description: Tóm tắt 2-3 ý ngắn gọn cốt lõi, không chép đoạn văn quá dài dòng.

4. PHÂN BIỆT HONOURS vs CERTIFICATES vs LANGUAGES (RẤT QUAN TRỌNG):

- "honours" (Giải thưởng, Học bổng, Thành tích):
  + Chứa toàn bộ học bổng (Scholarship, Học bổng đầu vào, Học bổng khuyến khích...).
  + Chứa các giải thưởng cuộc thi hoặc danh hiệu học tập/công việc.
  + NẾU CV KHÔNG CÓ THÀNH TÍCH/HỌC BỔNG: BẮT BUỘC ĐỂ MẢNG RỖNG [].

- "certificates" (Chứng chỉ nghề nghiệp / kỹ thuật):
  + CHỈ trích xuất các chứng chỉ nghề nghiệp/khóa học được ghi TRỰC TIẾP trong CV.
  + KHÔNG đưa học bổng vào certificates.
  + KHÔNG đưa điểm thi ngoại ngữ vào certificates.
  + NẾU CV KHÔNG CÓ MỤC CHỨNG CHỈ HOẶC KHÔNG CÓ CHỨNG CHỈ NÀO: BẮT BUỘC TRẢ VỀ MẢNG RỖNG []. TUYỆT ĐỐI KHÔNG TỰ BỊA RA BẤT KỲ CHỨNG CHỈ NÀO.

- "languages" (Ngoại ngữ):
  + Chứa tên ngôn ngữ ("language") và điểm số/trình độ ("note").
  + Điểm số ngoại ngữ đã vào languages thì KHÔNG đưa vào honours hoặc certificates.
  + NẾU CV KHÔNG CÓ NGOẠI NGỮ: BẮT BUỘC ĐỂ MẢNG RỖNG [].

5. SKILLS & TECH STACK
- skills: Kỹ năng chung liệt kê trong CV.
- tech_stack: Chỉ công nghệ của riêng từng dự án.

6. ĐỊNH DẠNG ĐẦU RA
Chỉ trả về DUY NHẤT một JSON hợp lệ. Không Markdown, không code fences, không giải thích nội dung.
"""

JSON_SCHEMA = """
Schema:

{
  "personal_info": {
    "full_name": null,
    "email": null,
    "phone": null,
    "github_url": null
  },

  "objective": null,

  "education": [],

  "experience": [],

  "personal_projects": [],

  "skills": [],

  "certificates": [],

  "honours": [],

  "languages": []
}

Cấu trúc từng phần tử khi CÓ dữ liệu trong CV:
- education item: {"school": str, "major": str, "start_year": str/int, "end_year": str/int, "gpa": str}
- experience item: {"company": str, "job_title": str, "start_date": str, "end_date": str, "description": [str]}
- personal_projects item: {"name": str, "role": str, "team_size": int, "start_date": str, "end_date": str, "github_url": str, "description": [str], "tech_stack": [str]}
- languages item: {"language": str, "note": str}
"""
JSON_SCHEMA_FORMAT = JSON_SCHEMA


def build_prompt_gguf(cv_text: str) -> str:
    # 1. Dựng Prompt với thẻ think đóng sẵn và mớm ký tự '{'
    prompt = f"""<|im_start|>system
{SYSTEM_PROMPT}

{JSON_SCHEMA_FORMAT}
<|im_end|>
<|im_start|>user
{cv_text}<|im_end|>
<|im_start|>assistant
<think>

</think>
{{"""
    return prompt
