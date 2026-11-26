# T04 · Ingest CV: A1–A9 (CV JSON → `cv_record`)

**Đọc trước:** [[00 Tổng quan kế hoạch]] · Thiết kế `04` A1–A9 (toàn bộ) · `03` mục "`cv_record` là gì", "Quyền riêng tư" · `11` mục 1.1, 3.3.

## Mục tiêu

Một hàm thuần `build_cv_record(raw_json, ctx) -> CvRecord` chạy A1→A9, **không DB, không GPU**. Kiểm tra trùng (A2) cần DB nên tách thành hàm nhận vào "kho tra cứu" (interface), để T05 nối DB thật.

## Làm

Mỗi bước một file trong `ingest/cv/`, mỗi file một hàm `step(record, ctx) -> record`:

| File | Bước | Điểm cần làm đúng |
| --- | --- | --- |
| `schema.py` + `adapter.py` | A1 | pydantic model CV theo JSON giả định ở thiết kế 04; **`adapter` đổi tên trường** từ schema thật (Q-1) sang model nội bộ. Trường tuỳ chọn thiếu → rỗng. Sửa ngày về `YYYY-MM` (dùng `parse_ym`), lỗi → `null` + cờ `date_unparsed`. Không có kinh nghiệm/dự án/kỹ năng → cờ `low_content`. Sai schema → `InvalidCV(errors)` |
| `dedup.py` | A2 | `content_hash` = SHA-256 của canonical JSON; `candidate_key` = HMAC(email chuẩn hoá) hoặc HMAC(sđt bỏ `+84`/khoảng trắng); không có → `null` + cờ `no_identity`. Nhận `DedupLookup` (interface: `find_by_hash`, `latest_version(candidate_key)`) → `Duplicate` hoặc `version` |
| `anonymize.py` | A3 | bỏ trường theo bảng A3; quét `summary`/`description` xoá email, sđt, chuỗi trùng `full_name` (cả dạng không dấu); bỏ `school`. Đầu ra `anon_json` |
| `normalize.py` | A4 | location → mã; `is_current` → `end` = tháng nạp (`ctx.ingest_ym`); chuẩn hoá mọi ô chữ **tại chỗ** trong `anon_json`; đồng thời giữ bản `text_raw` cho gạch, `summary`, mô tả dự án; cờ `no_diacritics` |
| `skills.py` | A5 | dùng `SkillMatcher`; `ev` theo vị trí (1,0 description · 0,8 technologies · 0,6 skills/summary/certificates — đọc từ config), lấy max; `source_field` dạng `experiences[0].description[1]`; `evidence_snippet`; `last_used`; liên kết tạm tới gạch (vị trí) để T05 điền `bullet_id`; phần tử `skills`/`technologies` không khớp → `unknown_skills` |
| `meta.py` | A6 | `years_experience` gộp khoảng chồng lấn (ví dụ 48 tháng ở thiết kế); `intern_months` riêng; thiếu `start` → cờ `years_uncertain`; `role_group`, `level_rank`, `level_source` (`title`/`inferred` — quy tắc suy từ số năm đặt trong config, Q mở 9); `major_group`; danh sách `experiences` (kind, role_group + `role_group_src` rule/keyword, months, `dates_quality`) và `education` (status, `expected_end_ym`) |
| `bullets.py` | A7 | mảng → mỗi phần tử một gạch; đoạn văn → tách theo xuống dòng / ký tự gạch / dấu câu; bỏ gạch < `bullet.min_words` và gạch chỉ có ngày; `text`, `text_raw`, `context_text` = `chức danh: gạch` (dự án: `tên dự án: gạch`); `section`, `item_idx` (0 = mới nhất), `pos`; cờ `has_negation`, `is_coursework` |
| `doc_text.py` | A8 | ghép theo **đúng mẫu** ở thiết kế, kinh nghiệm mới → cũ, không tên công ty/trường; phiên bản mẫu nằm trong `pipeline_version` |
| `bm25_tokens.py` | A9 | `bm25_noacc`, `bm25_acc`, `skill_tokens` — ba trường riêng |

`pipeline.py`: `build_cv_record(...)` gọi lần lượt, trả về `CvRecord` (pydantic) khớp cấu trúc ở thiết kế 03 (thiếu `vectors`).

## Không làm

Embedding (A10), ghi DB (A11), CLI → T05.

## Tiêu chí xong

- **Test vàng bằng CV mẫu của thiết kế 04**: kết quả phải khớp từng bảng ví dụ trong tài liệu — 5 dòng `cv_skill` (Spring Boot 1,0; PostgreSQL 1,0; Java 0,8; Kafka 0,8; Docker 0,6), `years_experience = 4,7` với `ingest_ym = 2026-11`, `role_group = Backend`, `level_rank = 4`, `major_group = it`, 2 gạch đúng `text_raw`/`context_text`, `doc_text` đúng mẫu.
- Test gộp chồng lấn: 2019-01→2020-06 + 2020-03→2022-12 = 48 tháng.
- Test ẩn danh: `anon_json`, `doc_text` không còn tên, email, sđt, tên trường (kể cả khi tên lẫn trong `summary`).
- Test cờ: CV gõ không dấu → `no_diacritics`; gạch "Chưa từng triển khai Kubernetes" → `has_negation`; "Bài tập lớn môn CSDL" → `is_coursework`.
- Test tái lập: chạy hai lần cùng đầu vào → `CvRecord` giống hệt.

## Ghi chú bàn giao

**Trạng thái: xong (15/11/2026).** 22 test (`tests/unit/test_ingest_cv.py`), toàn bộ 79 test qua. Khoảng 1,8 ms/CV với CV mẫu (chưa đo CV thật).

- **Điểm vào:** `ingest/cv/pipeline.py: build_cv_record(raw, ctx) -> CvRecord`. `CvContext.create(cfg, snapshot, hmac_key=, ingest_ym=, dedup=)` tạo một lần cho cả lô. Dừng sớm: `InvalidCV(errors)` (A1), `DuplicateCV(existing_cv_id)` (A2). `InMemoryDedup` để test; **T05 cài `DedupLookup` trên Postgres**.
- **Cho T05 biết:**
  - `SkillFound.bullet_ref = (section, item_idx, pos)` → A11 tra ra `bullet_id` sau khi chèn `cv_bullet`.
  - `CvRecord.replaces_cv_id` = bản cũ cùng `candidate_key` → A11 đặt `is_latest = false`.
  - `CvRecord.anon_raw` và `item_order`, `date_year_only` chỉ dùng trong RAM, **không ghi DB**.
  - `cv_experience` có thêm trường `section`, `src_index` trong record (không có cột; `section` suy được từ `kind`).
- **Quyết định đã đưa vào code (lệch hoặc chi tiết hoá thiết kế):**
  - **Đếm tháng:** tính cả hai đầu; việc đang làm không tính tháng hiện tại. Đây là quy tắc duy nhất khớp cả hai ví dụ của A6 (56 tháng và 48 tháng). Đặt ở `core/timeutil.py` để B2 dùng lại.
  - `years_experience` chỉ tính mục `job` (không dự án, không thực tập). CV không có mục kinh nghiệm nào → `0.0`; có mục nhưng không mục nào tính được → `NULL`.
  - `source_field` của `technologies`/`skills` có chỉ số phần tử (`experiences[0].technologies[0]`), chính xác hơn bảng ví dụ.
  - `item_idx` / `cv_experience.idx` theo thứ tự mới → cũ; `source_field` giữ chỉ số mảng JSON gốc.
  - `content_hash` tính trên JSON **đầu vào** (trước adapter). `candidate_key = "hmac:" + HMAC-SHA256(key, "email:<email>" | "phone:<sđt>")`; sđt `+84…` / `84…` → `0…`.
  - Nhóm vai trò theo từ khoá dùng `config/patterns/role_keywords.yaml` (snapshot KB chưa có `USED_IN`).
  - Kỹ năng lạ chỉ ghi khi phần tử ≤ 4 từ và ≤ 40 ký tự (cụm dài như "làm việc nhóm tốt…" không coi là tên kỹ năng).
  - A3 thêm cờ `suspected_injection` (thiết kế 08 mục 6) và xoá cả URL trong chữ tự do; tên được xoá cả dạng không dấu và đảo họ/tên.
  - Ngày chỉ có năm → `dates_quality = partial`; học vấn ghi "đang học" ở `end` → `status = studying`.
  - `doc_text`: nhiều mục nối bằng " | ". Token BM25 tách trên nội dung, **bỏ nhãn dòng** ("Chức danh:"…).
- **Còn giả định:** tên trường JSON (Q-1) — sửa ở `adapter.py`; quy tắc suy cấp bậc từ số năm (`prep.level_from_years`); phân biệt `project_team` / `project_personal` (theo `kind` hoặc `team_size > 1`).
