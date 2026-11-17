# Feature 016 — Mở rộng Module 1 (intern / fresher)

Trạng thái: **mô tả để xây dựng sau**, chưa implement. Mỗi feature dưới đây đi qua Spec Kit (spec → clarify → plan → tasks) khi bắt đầu.

Phạm vi chung:
- Model mới chỉ phục vụ **intern và fresher** (xem [015 plan](../015-real-image-dataset/plan.md)).
- Hệ thống phục vụ nhà tuyển dụng theo hướng **tự động**: nhà tuyển dụng không duyệt từng CV. Bước kiểm tra do **ứng viên** làm trên hồ sơ của chính họ (màn hình `ui-prototype/candidate/cv.html`, bước "3. Xác nhận").
- **Hợp đồng `POST /api/v1/extract-cv` không đổi mặc định.** Trường mới chỉ trả khi gọi `?include=…` (giống `kg`, `raw` hiện có). Đổi output mặc định phải xin xác nhận (constitution).
- Dữ liệu CV thật chỉ lưu nội bộ; log chỉ ghi số đếm.

Hiện trạng liên quan (17/11/2026):
- AI service: grounding đã tìm vị trí từng giá trị trong text CV (`app/postprocess/grounding.py`) nhưng chưa trả ra; KB/KG trả qua `?include=kg`.
- Backend: Spring Boot, PDFBox + XY-cut; **chưa có database / entity** (chưa cấu hình datasource); pom đã có `tess4j` (Tesseract cho Java).
- Frontend: React mới có trang chủ + đăng nhập; các màn hình Module 1 mới ở `ui-prototype/` (HTML tĩnh, dữ liệu giả).

Thứ tự đề xuất: **F2 → F1 → F3 → F5 → F4** (F2 độc lập, không cần train; F1 dùng chung công cụ với feature 015; F3 dùng lại OCR của 015).

---

## F1 — Độ tin cậy + bằng chứng cho từng trường; ứng viên xác nhận; bản sửa thành dữ liệu train

### Mục tiêu
1. Mỗi giá trị trích xuất có **bằng chứng** (đoạn text gốc trong CV) và **độ tin cậy**.
2. Ứng viên xem trước hồ sơ, các trường độ tin cậy thấp được tô sáng, sửa rồi xác nhận.
3. Phía nhà tuyển dụng tự động: hồ sơ độ tin cậy thấp được tự chạy lại / gắn cờ, không bắt duyệt tay.
4. Bản ứng viên đã sửa trở thành nhãn train → **giảm công gán nhãn** khi train lại (không bỏ việc train lại).

### Thiết kế output (`?include=confidence`)
```json
"confidence": {
  "overall": 0.86,
  "fields": {
    "experience[0].company":    {"level": "high",   "method": "exact", "evidence": {"start": 412, "end": 431}},
    "experience[0].start_date": {"level": "low",    "method": "date_order_swapped"},
    "skills[3]":                {"level": "medium", "method": "fuzzy", "score": 88}
  },
  "flags": ["MISSING_SECTION:personal_projects", "DATE_ORDER_FIXED"]
}
```
- `evidence` là vị trí (offset) trong `cv_text`, không chép lại nội dung → không tăng lượng dữ liệu cá nhân trong response/log.
- Quy tắc mức (tất định, giải thích được):
  - `high`: khớp nguyên văn trong text (grounding exact).
  - `medium`: khớp mờ (fuzzy ≥ 85), hoặc giá trị đã bị sửa bởi hậu kiểm (tách ngoặc kỹ năng…).
  - `low`: ngày bị đổi chỗ / thiếu, chức danh bị null, trường lấy từ sinh nối tiếp, mục có tiêu đề trong CV nhưng JSON rỗng ("Dự án", "Kinh nghiệm" xuất hiện mà danh sách rỗng).
  - `overall`: tỷ lệ trường high có trọng số (company, school, ngày, skills nặng hơn).

### Triển khai
**AI service**
- `app/postprocess/grounding.py`: ghi lại `(path, method, score, start, end)` cho mỗi giá trị được giữ (hiện chỉ đếm số bị loại).
- `app/postprocess/confidence.py` (mới): gom kết quả grounding + thống kê hậu kiểm (`dates_swapped`, `titles_nulled`, `continued`…) + quét tiêu đề mục trong text → `confidence`.
- `app/api/routes.py`: thêm giá trị `confidence` cho tham số `include`.
- Test: CV hư cấu với từng trường hợp (exact, fuzzy, ngày đảo, mục rỗng); kiểm tra offset trỏ đúng đoạn text.

**Backend**
- Thêm datasource PostgreSQL + JPA (lần đầu backend có database). Bảng:
  - `cv_document(id, file_hash, text_hash, text_mode, created_at)` — không lưu file gốc lâu dài nếu không cần.
  - `cv_extraction(id, cv_document_id, model_version, prompt_version, raw_output_json, confidence_json, created_at)`.
  - `cv_profile_confirmed(id, cv_extraction_id, confirmed_json, edited_paths, confirmed_by, confirmed_at, consent_training boolean)`.
- API mới:
  - `POST /api/v1/cv/analyze-pdf?include=confidence` → trả profile + confidence + `extractionId`.
  - `PUT /api/v1/cv/extractions/{id}/confirm` → lưu bản xác nhận, tính `edited_paths` (diff với output model).
- Luồng nhà tuyển dụng (nếu có upload hàng loạt):
  - `overall` thấp → tự chạy lại một lần bằng cách khác (bật sinh nối tiếp tối đa, hoặc trích xuất theo từng mục / model dự phòng), lấy kết quả có `overall` cao hơn.
  - Vẫn thấp → đưa vào matching bình thường, gắn cờ `NEEDS_REVIEW`; Module 2 giảm trọng số các trường `low`.

**Frontend** (màn hình hồ sơ ứng viên, theo `ui-prototype/candidate/cv.html`)
- Bước 3 "Xác nhận": form các trường; trường `low` viền đỏ, `medium` viền vàng; vòng tròn = `overall`; dòng "Thiếu / chưa chắc" lấy từ `flags`.
- Bấm vào trường → hiện đoạn text gốc (dùng `evidence` offset trên text đã trích xuất).
- Checkbox đồng ý dùng dữ liệu để cải thiện hệ thống (`consent_training`).
- Phía nhà tuyển dụng (`recruiter/candidates.html`): chỉ hiện nhãn nhỏ "nên xem CV gốc" cho hồ sơ `NEEDS_REVIEW`.

**Thu dữ liệu train từ bản xác nhận**
- Script `ai-service/training/collect_confirmed.py`: xuất từ DB các bản có `consent_training = true` **và** `edited_paths` không rỗng.
- Chỉ nhận vào nhãn những giá trị **tìm thấy trong text CV** (dùng lại grounding). Giá trị ứng viên thêm ngoài CV (vd tự thêm kỹ năng) vẫn dùng cho matching nhưng **không** vào train — tránh dạy model bịa.
- Chạy lint quy ước nhãn (feature 015). Lấy ngẫu nhiên ~10 % để người duyệt kiểm tra lại.
- Chỉ đưa vào **train**; tập test cố định (015) không lấy từ nguồn này.

### Tiêu chí chấp nhận
- Output mặc định không đổi; `?include=confidence` trả đúng schema; offset evidence đúng với 100 % giá trị `high` trên bộ test hư cấu.
- Trên test thật: các trường sai thực tế phần lớn rơi vào `medium`/`low` (đo recall của cờ `low` trên lỗi của v4).
- Bản xác nhận được lưu, diff đúng; script thu dữ liệu chỉ xuất giá trị grounded.

### Ước lượng
AI service ~2 ngày; backend (DB + API) ~3 ngày; frontend ~2–3 ngày (khi React có màn hình hồ sơ).

---

## F2 — Trường suy diễn cho intern / fresher (logic tất định, không cần train)

### Mục tiêu
Model chỉ chép nguyên văn; Module 2 cần số liệu để so khớp. F2 tính thêm các trường chuẩn hoá từ JSON đã trích xuất.

### Thiết kế output (`?include=derived`)
```json
"derived": {
  "experience_months_total": 7,
  "internship_count": 2,
  "education_status": "studying",          // studying | graduated | unknown
  "graduation_year": 2026,                 // năm tốt nghiệp / dự kiến
  "study_year": 4,                         // năm học hiện tại nếu đang học
  "gpa_4": 3.2,                            // quy về thang 4
  "gpa_source": "8.0/10",
  "english": {"cefr": "B2", "source": "TOEIC 750"},
  "project_count": 3,
  "level_guess": "intern"                  // intern | fresher | unknown
}
```

### Quy tắc
- **Ngày**: parse "03/2021", "Mar 2021", "2021-03", "T3/2021", "Tháng 3/2021", "2021"; "Present/Hiện tại/Now" = ngày xử lý. Gộp các khoảng chồng nhau trước khi cộng tháng.
- **experience_months_total**: tổng tháng của `experience` (đã gộp chồng lấn). `internship_count`: job_title chứa intern/thực tập/trainee.
- **Học vấn**: `end_year` > năm hiện tại hoặc CV ghi "hiện tại/expected/dự kiến" → `studying`; `study_year` = năm hiện tại − `start_year` + 1 (giới hạn 1–6).
- **GPA**: nhận "x/4", "x/10", "x/100", "x" (đoán thang theo giá trị: ≤ 4 → thang 4, ≤ 10 → thang 10). Quy đổi thang 10 → 4 theo bảng quy đổi tín chỉ phổ biến ở Việt Nam (8,5–10 → 4,0; 7,0–8,4 → 3,0–3,9 tuyến tính…); lưu nguồn gốc để giải thích.
- **Tiếng Anh**: TOEIC (L&R) → CEFR theo bảng ETS (≥ 945 C1, ≥ 785 B2, ≥ 550 B1…); IELTS → CEFR theo bảng British Council; "Fluent/Thành thạo" → C1, "Intermediate/Khá" → B1 (mức thấp, ghi `method: text`).
- **level_guess**: đang học hoặc chỉ có thực tập → `intern`; tốt nghiệp ≤ 2 năm và kinh nghiệm < 24 tháng → `fresher`; còn lại `unknown`.

### Triển khai
- `ai-service/app/derive/` (mới): `dates.py` (dùng lại `app/postprocess/dates.parse_month` và mở rộng định dạng), `gpa.py`, `english.py`, `derive.py` (`derive_profile(profile, today) -> dict`).
- `routes.py`: `include=derived`. Chạy sau hậu kiểm, trước chuẩn hoá KB (dùng giá trị nguyên văn).
- Bảng quy đổi để trong file dữ liệu (`app/derive/tables.json`) kèm nguồn trích dẫn (ETS, British Council, quy chế đào tạo tín chỉ).
- Test: bảng ca kiểm thử cho từng hàm (định dạng ngày, chồng lấn, Present, GPA biên 8,5 / 7,0, TOEIC biên 785, IELTS 6.5…); 100 % tất định.

### Tiêu chí chấp nhận
- Toàn bộ test đơn vị đạt; trên test thật, `experience_months_total` và `graduation_year` khớp tính tay ở ≥ 95 % CV (khi ngày được trích đúng).
- Output mặc định không đổi.

### Ước lượng
~1–2 ngày.

---

## F3 — Mở rộng input: DOCX/DOC/ODT, ảnh, OCR dự phòng, CV dạng link, kiểm tra đầu vào

### F3a — Nhận .docx
- Backend: `analyze-pdf` nhận thêm `.docx` (giữ tên endpoint hoặc thêm `/analyze-file`). Chuyển DOCX → PDF bằng LibreOffice headless (`soffice --convert-to pdf`, chạy trong thư mục tạm, timeout 60 s, profile riêng) rồi đi đúng pipeline PDF hiện có (XY-cut).
- Lý do qua PDF thay vì đọc DOCX trực tiếp: giữ một đường xử lý, một kiểu text cho model (train/serve giống nhau).
- Cần LibreOffice trên máy chạy backend (Dockerfile cài `libreoffice-writer`).
- Test: DOCX hư cấu 1 cột, 2 cột (bảng), có ảnh.

### F3b — OCR dự phòng cho PDF scan / ảnh
- Phát hiện: `PdfTextExtractor` trả ít hơn `MIN_TEXT_CHARS` (hiện đang từ chối "có thể là file ảnh scan").
- Xử lý: render trang thành ảnh (PDFBox `PDFRenderer`, 300 dpi) → OCR (tess4j `vie+eng`, đã có trong pom; hoặc dùng lại công cụ ảnh → PDF có lớp chữ của feature 015) → tạo lại danh sách từ + toạ độ → chạy XY-cut như PDF thường.
- Đánh dấu `text_source = "ocr"` trong response; F1 hạ độ tin cậy mặc định của hồ sơ OCR một bậc.
- Ngưỡng chất lượng lấy từ Giai đoạn 0 của feature 015 (CER trên 59 PDF thật).
- Nhận thêm ảnh `.png/.jpg` qua cùng đường.

### F3d — Định dạng khác và CV dạng link
- `.doc`, `.odt`, `.rtf`: như F3a (LibreOffice → PDF → pipeline PDF).
- Ảnh `.png/.jpg/.webp`: qua F3b (OCR).
- Link Google Drive / OneDrive công khai (thường gặp trong email): tải file (giới hạn dung lượng, chỉ domain cho phép, timeout) rồi xử lý như file thường.
- Link hồ sơ TopCV / ITviec / LinkedIn: **không** tự lấy (cần đăng nhập, điều khoản không cho thu thập tự động) → gắn cờ `CV_AS_LINK`, nhà tuyển dụng tự tải.

### F3c — Kiểm tra đầu vào
- Từ chối / cảnh báo sớm, trước khi gọi model (tiết kiệm 15–40 s):
  - Không phải CV: text không có tín hiệu CV (không email/điện thoại, không tiêu đề mục quen thuộc) → 422 `NOT_A_CV`.
  - Nhiều CV trong một file: nhiều cụm email/điện thoại + tên ở đầu trang khác nhau → cảnh báo `MULTIPLE_CVS`.
  - Ngôn ngữ ngoài vi/en, quá 10 trang (đã có), file mã hoá mật khẩu.
- Triển khai ở backend (`extraction/validation/CvValidator.java` đã có, mở rộng) để không gọi AI service khi đầu vào sai.

### Tiêu chí chấp nhận
- DOCX và PDF cùng nội dung cho text giống nhau ≥ 95 % (so sau chuẩn hoá).
- PDF scan hư cấu: trích xuất được, F1 không thấp hơn PDF gốc quá ngưỡng của 015.
- Bộ kiểm thử file không phải CV (hoá đơn, bài báo hư cấu) bị từ chối đúng.

### Ước lượng
F3a ~1 ngày; F3b ~2–3 ngày (sau Giai đoạn 0 của 015); F3c ~1 ngày.

---

## F4 — Vận hành: cache và thống kê

### F4a — Cache theo hash
- Backend tính `sha256` của file (và `text_hash` của text trích xuất). Cùng file + cùng `model_version` + `prompt_version` + `text_mode` → trả kết quả đã lưu (bảng `cv_extraction` của F1), không gọi model lại.
- Đổi model / prompt / extractor → khoá cache khác, tự tính lại.
- Có tham số `?refresh=true` để bỏ qua cache khi cần.
- Không có DB (trước F1): dùng cache trong bộ nhớ (Caffeine, giới hạn kích thước, TTL), chỉ giữ JSON kết quả.

### F4b — Thống kê chất lượng (chỉ số đếm)
- AI service đã có số đếm hậu kiểm; ghi thêm theo từng request (không nội dung CV): số token, `truncated`, `continued`, số giá trị bị grounding loại, số kỹ năng không link được KB, `overall` confidence, thời gian.
- Xuất qua endpoint Prometheus (`/metrics`, `prometheus-fastapi-instrumentator` / Spring Actuator đã có) hoặc ghi JSONL số đếm.
- Bảng theo dõi (Grafana hoặc trang đơn giản): tỷ lệ bị cắt, tỷ lệ hồ sơ `low`, tỷ lệ ứng viên sửa (từ F1) theo phiên bản model → biết khi nào cần train lại.
- **Danh sách kỹ năng chưa có trong KB**: gom tên kỹ năng unlinked (chỉ tên kỹ năng, không kèm CV), đếm tần suất → gợi ý bổ sung KB định kỳ (kiểm tra nguồn trước khi thêm, giữ nguyên tắc KB có nguồn của feature 009).

### Tiêu chí chấp nhận
- Upload lại cùng CV trả kết quả < 200 ms; đổi `PROMPT_VERSION` thì tính lại.
- Metrics không chứa bất kỳ chuỗi nào từ CV (test kiểm tra log/metrics với CV hư cấu có chuỗi đánh dấu).

### Ước lượng
F4a ~1 ngày (in-memory) / thêm 0,5 ngày khi có DB; F4b ~1–2 ngày.

---

## F5 — Tự động lấy CV từ email tuyển dụng

### Mục tiêu
Thay việc nhà tuyển dụng upload hàng loạt: CV ứng viên gửi về hộp thư tuyển dụng được tự động lấy, trích xuất và đưa vào matching.

### Lựa chọn kỹ thuật
| Cách | Đánh giá |
|---|---|
| **IMAP polling** hộp thư tuyển dụng riêng (khuyến nghị) | Đơn giản, chạy với Gmail và Microsoft 365, dữ liệu không qua bên thứ ba; trễ 1–5 phút |
| Push: Gmail API `watch` + Pub/Sub / Microsoft Graph subscription | Gần tức thời; cấu hình phức tạp (đăng ký app, webhook công khai) — cân nhắc sau |
| Forward sang dịch vụ inbound parse (SendGrid, Mailgun) | CV đi qua bên thứ ba → **không dùng** (bảo mật dữ liệu CV) |

### Luồng (IMAP)
1. **Kết nối**: Spring Integration Mail / Jakarta Mail, **OAuth2** (Microsoft 365 đã bỏ basic auth; Gmail dùng OAuth2 hoặc app password). Credential trong biến môi trường / kho secret; chỉ quyền đọc hộp thư tuyển dụng.
2. **Lấy thư**: định kỳ 1–5 phút, thư chưa xử lý; bỏ auto-reply, bounce, newsletter (header `Auto-Submitted`, `List-Unsubscribe`); khử trùng `Message-ID` + `sha256` file; đánh dấu đã xử lý (flag hoặc chuyển thư mục "Đã xử lý").
3. **Tách nội dung**: file đính kèm pdf/docx/doc/odt/ảnh; bỏ ảnh inline nhỏ (chữ ký, logo: `Content-Disposition: inline`, < ~30 KB); link Drive/OneDrive trong body → F3d.
4. **Gắn tin tuyển dụng**: plus-addressing theo tin (`tuyendung+<job-id>@…`) hoặc khớp tiêu đề thư với tên tin; không xác định được → nhóm "Chưa phân loại".
5. **Kiểm tra file**: giới hạn dung lượng, quét virus (ClamAV), F3c loại file không phải CV (thư xin việc, bảng điểm, chứng chỉ); nhiều file → chọn file có điểm "là CV" cao nhất, các file còn lại lưu kèm.
6. **Xử lý**: F3 (chuyển đổi / OCR) → trích xuất → F1 (độ tin cậy, chạy lại / gắn cờ) → Module 2. Email người gửi lưu làm liên hệ dự phòng nếu CV thiếu email.
7. **Phản hồi (tuỳ chọn)**: thư tự động xác nhận đã nhận CV + link để ứng viên xem/xác nhận hồ sơ (F1) + thông báo xử lý dữ liệu cá nhân.
8. **Theo dõi**: màn hình nhà tuyển dụng — CV từ email theo trạng thái: mới, đang xử lý, đã trích xuất, cần xem CV gốc, lỗi (kèm lý do: không phải CV, file hỏng, link cần đăng nhập).

### Dữ liệu (backend, cùng DB với F1)
- `mail_message(id, message_id UNIQUE, received_at, sender_email, subject_hash, job_id NULL, status)` — không lưu toàn văn thư nếu không cần.
- `mail_attachment(id, mail_message_id, file_hash, mime, size, is_cv, cv_document_id NULL)`.

### Bảo mật và pháp lý
- Chỉ hộp thư tuyển dụng riêng, không đọc hộp thư cá nhân.
- CV từ email là dữ liệu cá nhân (Nghị định 13/2023): dùng cho mục đích tuyển dụng; thư phản hồi kèm thông báo xử lý dữ liệu; **chỉ đưa vào dữ liệu train khi ứng viên đồng ý** qua bước xác nhận F1.
- Log chỉ ghi số đếm và trạng thái, không ghi nội dung thư / CV.

### Tiêu chí chấp nhận
- Với hộp thư thử nghiệm và thư hư cấu: lấy đủ CV đính kèm (pdf, docx, ảnh), bỏ ảnh chữ ký, không xử lý trùng khi chạy lại, gắn đúng tin theo plus-address, thư không có CV được đánh dấu đúng lý do.
- Mất kết nối / lỗi OAuth không làm mất thư (thư chỉ được đánh dấu đã xử lý sau khi lưu thành công).

### Ước lượng
~3–4 ngày (sau khi có DB của F1 và F3a/F3c).

---

## Phụ thuộc giữa các feature

| Feature | Phụ thuộc | Dùng chung với |
|---|---|---|
| F2 | không | Module 2 (đầu vào so khớp) |
| F1 | DB backend; frontend màn hình hồ sơ | 015: lint nhãn, builder dataset, công cụ duyệt |
| F3b | 015 Giai đoạn 0 (đo OCR) | 015 Giai đoạn 1 (ảnh → PDF có lớp chữ) |
| F4a | (tốt hơn khi có DB của F1) | F1 |
| F4b | không | F1 (tỷ lệ ứng viên sửa) |
| F5 | DB của F1; F3a, F3c (F3b, F3d nếu nhận ảnh / link) | F1 (ứng viên xác nhận qua link trong thư phản hồi) |
