"""Hằng số dùng chung cho KB1, KB2 và load_kb.py."""

# Nhóm vai trò của thiết kế (Knowledge base.md, mục 1). 5 nhóm cuối thêm ở KB3 (21/11/2026) cho các chức danh
# ITviec không thuộc 9 nhóm ban đầu. Thứ tự là thứ tự ưu tiên khi chức danh thuộc nhiều nhóm.
ROLE_GROUPS = ["Backend", "Frontend", "Fullstack", "Mobile", "Data", "AI/ML", "DevOps", "QA", "Security",
               "Embedded", "Game", "Design", "Business", "IT Support"]

# Thang cấp bậc (Knowledge base.md, mục 1)
LEVEL_RANKS = {"Intern": 0, "Fresher": 1, "Junior": 2, "Mid": 3, "Senior": 4, "Lead": 5}
