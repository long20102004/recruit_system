# T06 · Ingest JD: Luồng B (B1–B8)

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `05` (toàn bộ) · `04` A4, A5, A7, A9 (vì B dùng lại) · `03` "Các bảng".

## Mục tiêu

Nạp JD JSON của Module 1 thành các bảng `jd*`, dùng lại **cùng** hàm chuẩn hoá, SkillMatcher, encoder, writer như Luồng A.

## Làm

Trong `ingest/jd/`, cùng kiểu một bước một file:

| Bước | Điểm cần làm đúng |
| --- | --- |
| B1 `schema.py` + `adapter.py` | tối thiểu `title` + một trong `skills`/`requirements`/`responsibilities`; `jd_id` lấy từ Module 1; `version` = max + 1 |
| B2 | gọi đúng `core/text.normalize` → `norm_json` |
| B3 | `query_text` theo đúng mẫu (Chức danh / Kỹ năng / Yêu cầu / Trách nhiệm); bỏ `company_intro`, `benefits`… |
| B4 | `skills[]` → skill_id; dò thêm trong `requirements` → `required = false`, `source = requirements`; `w_imp` từ `importance` (thiếu → 1,0); nhóm "A hoặc B" ("Java hoặc Kotlin", "MySQL/PostgreSQL") → chung `group_id`; không khớp → `unknown_skill` |
| B5 | `jd_meta` (`min_years`/`max_years` từ JSON hoặc regex trên `requirements`: "tối thiểu 4 năm", "3–5 năm"; `level_rank`, `role_group` từ `title`; `edu_required`); phân loại từng dòng `requirements` → `kind ∈ {years, degree, language, skill_only, text}` theo quy tắc thiết kế (ưu tiên `years`) |
| B6 | trách nhiệm < `min_words` bỏ; `is_generic` theo danh sách mẫu; `text`, `text_raw`, `context_text` |
| B7 | `bm25_query_tokens` (giống A9 + skill token); dense + sparse của `query_text`; dense mỗi trách nhiệm |
| B8 | cảnh báo vào `jd.warnings` (không có kỹ năng bắt buộc; không có trách nhiệm không-generic; `query_text` < `jd.min_query_words`; > 30% kỹ năng không gắn mã); ghi một giao dịch đúng thứ tự thiết kế; bản cũ `is_latest = false`; giữ `status` từ JSON |

- CLI: `cvmatch ingest jd <file|thư mục>`, `cvmatch jd status <jd_id> open|closed` (chỉ đổi `status`, không tính lại).
- Phát sự kiện `JdCommitted` / `JdStatusChanged` (cho Luồng D sau này).

## Tiêu chí xong

- **Test vàng bằng JD mẫu thiết kế 05**: 5 dòng `jd_skill` đúng bảng B4 (Microservices tìm thêm từ `requirements`, `w_imp = 0,4`); `jd_meta` = (`ho_chi_minh`, `hybrid`, 4, NULL, 4, Backend, NULL); `jd_requirement_item`: dòng 0 `years`, dòng 1 `text`; trách nhiệm idx 2 `is_generic = true`; `warnings = []`.
- Test "A hoặc B": "MySQL/PostgreSQL" → 2 dòng cùng `group_id`.
- Test phân loại: "Tốt nghiệp ĐH chuyên ngành CNTT" → `degree`, `edu_required = it_related`; "Đọc hiểu tài liệu tiếng Anh" → `language`; "Thành thạo Java và Spring Boot" → `skill_only`.
- Sửa JD → `version = 2`; đổi status không tạo version mới.
- Kiểm tay sau T06 (mốc): nạp CV + JD mẫu, xem đủ 17 bảng.

## Ghi chú bàn giao

**Trạng thái: xong (15/11/2026).** 26 test đơn vị (`tests/unit/test_ingest_jd.py`) + 4 test tích hợp (`tests/integration/test_ingest_jd_db.py`, gồm **mốc sau T06**: CV + JD mẫu → đủ 17 bảng có dữ liệu, CV và JD cùng bộ phiên bản). Toàn bộ 124 test qua.

- **Dùng:** `build_jd_record(raw, ctx, versions)` (B1–B7 trừ vector, + cảnh báo B8); `JdIngestor(conn, ctx, encoder).ingest_one/ingest_many`; `set_jd_status(conn, jd_id, status)`. CLI: `cvmatch ingest jd <path> --kb-dir … [--fake-encoder]`, `cvmatch jd status <jd_id> open|closed|draft|expired`. Ngữ cảnh dùng chung `CvContext` của Luồng A (cùng hàm chuẩn hoá, cùng KB).
- **Quyết định / lệch thiết kế:**
  - **Phân loại `skill_only`** chỉ bỏ kỹ năng loại `technology`; kỹ năng `concept` giữ lại → "Hiểu biết về microservices" là `text` (khớp ví dụ thiết kế; quy tắc chữ của thiết kế mâu thuẫn với ví dụ).
  - Kỹ năng tìm thêm từ `requirements`: `required = false`, `w_imp = minor (0,4)` (theo bảng ví dụ B4).
  - Nhóm "A hoặc B": hai kỹ năng liền nhau chỉ cách bởi `/`, `|`, `hoặc`, `hay`, `or` — áp cho cả phần tử `skills` và dòng `requirements`.
  - Gửi lại JD **giống hệt** bản mới nhất → `unchanged`, không tạo version (so `raw_json`).
  - Thiếu `status` hoặc giá trị lạ → `open`; có bảng alias ("đang tuyển" → open…).
  - Ngưỡng 50 từ của `short_query` đếm trên **toàn bộ `query_text` kể cả nhãn dòng** (ví dụ thiết kế có `warnings = []` chỉ đúng khi đếm như vậy).
  - `bm25_query_tokens` = token **không dấu** của nội dung truy vấn (bỏ nhãn) + skill token. Nếu Retrieve chọn `bm25.field = acc` thì cần thêm cột token có dấu (ghi nhận cho T09).
  - `raw_json` = JSON sau adapter, trường danh sách viết dạng đoạn văn được tách thành mảng.
  - Cảnh báo lưu dạng `{code, message}`: `no_required_skill`, `no_responsibility`, `short_query`, `many_unmapped_skills`.
- **Còn giả định:** tên trường JSON của Module 1 (Q-1) — sửa `TOP_LEVEL`/`SKILL` ở `ingest/jd/schema.py`; regex số năm, bằng cấp, ngoại ngữ (ƯL, cần kiểm trên JD thật ở T07).
