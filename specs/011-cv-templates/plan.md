# Plan · 011 Mẫu CV

## Kiến trúc: hai loại mẫu, một đầu ra

```
                       ┌─ CONFIG ─▶ CvHtmlRenderer (Thymeleaf, 2 layout) ─▶ HTML ─┬─▶ iframe xem trước (C04, AD06)
Mẫu + hồ sơ CV ──────▶ │                                                          └─▶ OpenHTMLtoPDF ─┐
                       └─ DOCX ───▶ CvDocxRenderer (poi-tl điền chỗ) ─▶ .docx ─▶ Gotenberg ─────────┴─▶ PDF ─▶ R2 private
```

`CvRenderService.render(template, profile, title) → PDF bytes` chọn nhánh theo `type`; nơi gọi (xem trước PDF, lưu CV,
tải file) không cần biết loại mẫu.

### Nhánh CONFIG
- Thymeleaf (escape mặc định), 2 layout XHTML trong `resources/templates/cv/` (`one-column.html`, `two-column.html`).
  Tuỳ chọn trình bày (căn phần đầu, kiểu tiêu đề, vị trí thời gian, độ dày, lề) là class/biến CSS trong layout,
  không phải layout riêng → thêm kiểu mới = thêm tuỳ chọn, không thêm file.
- Ví dụ Harvard: `ONE_COLUMN · Tinos · đen · CENTER · UPPERCASE_RULE · RIGHT_INLINE · COMPACT ·
  [info, education, experience, projects, honours, skills, languages, certificates]`.
- PDF: OpenHTMLtoPDF (fork hỗ trợ `pdfbox 3`, vì recruitment-service đang dùng `pdfbox 3.0.5`), font TTF (OFL) nhúng từ
  `resources/fonts/`. Spike T001.

### Nhánh DOCX
- Điền chỗ: **poi-tl** (trên Apache POI, đã có `poi-ooxml`). Ký hiệu (chốt cú pháp ở spike T002, ghi trong
  `docs/CV_TEMPLATE_DOCX.md`):
  - đơn: `{{full_name}}`, `{{email}}`, `{{phone}}`, `{{github}}`, `{{objective}}`, `{{title}}`
  - lặp: `{{?experience}} … {{job_title}} {{company}} {{location}} {{start_date}} {{end_date}} {{description}} … {{/experience}}`;
    tương tự `education`, `projects`, `languages`; danh sách chữ: `skills`, `certificates`, `honours`
  - mục trống thì cả khối bị ẩn (khối lặp không có phần tử).
- Kiểm tra khi tải lên: đuôi/MIME `.docx`, ≤ 2MB, không macro, quét ký hiệu → ký hiệu không hỗ trợ trả 400 kèm danh sách;
  điền thử hồ sơ mẫu tổng hợp → chuyển PDF → lưu file gốc + PDF xem trước + ảnh thu nhỏ (trang 1, PDFBox render PNG).
- Chuyển PDF: **Gotenberg** (`gotenberg/gotenberg:8`, LibreOffice) qua HTTP `POST /forms/libreoffice/convert`, chỉ mạng nội bộ,
  không ra Internet (không tải ảnh/link ngoài trong file), timeout 20s. Font trong file Word nên dùng font có trong Gotenberg
  (Noto, Liberation/Tinos…); font khác bị thay thế — ghi trong hướng dẫn.
- Xem trước cho ứng viên (C04): không có HTML → nút "Cập nhật xem trước" sinh PDF từ dữ liệu đang sửa, hiện bằng link ký tạm
  trong iframe (trình xem PDF của trình duyệt).

## Dữ liệu (recruitment-service, `V13__cv_templates.sql`)

```
cv_templates(id, name VARCHAR(80) UNIQUE, type ENUM CONFIG|DOCX, status ENUM ACTIVE|HIDDEN, is_default BOOL,
             config JSON NULL,                -- CONFIG: layout, font, accent, background, header, heading, dates,
                                              --         density, margin, sections[]
             docx_key VARCHAR(512) NULL,      -- DOCX: file gốc trên R2 (cv-templates/{id}/{uuid}.docx)
             preview_pdf_key, thumbnail_key VARCHAR(512) NULL,
             created_by INT, created_at, updated_at)
cv_documents + template_id INT NULL (FK RESTRICT), generated_pdf_key VARCHAR(512) NULL, generated_at DATETIME NULL
```

- Seed 4 mẫu CONFIG (Harvard mặc định). File Word mẫu Harvard để trong `resources/cv-templates/harvard-sample.docx`,
  tải qua API admin.
- Hồ sơ CV: thêm `location` vào `Education`, `Experience` (Java DTO + TS type + `normalizeProfile`/`cleanProfile` + form C04/C03).
  Dữ liệu lưu dạng JSON trong `cv_data`, không cần migration.
- Bảng tuỳ chọn (font, màu, nền, kiểu…) là hằng số backend `CvTemplateOptions`, FE lấy qua API.

## API

Admin — quyền mới `cv-template:manage` (identity `V9__cv_template_permission.sql`, `docs/RBAC.md`):

| Method | Path | Ghi chú |
|---|---|---|
| GET | `/api/admin/cv-templates` | tất cả + `usedCount`, `thumbnailUrl` (link ký tạm) |
| GET | `/api/admin/cv-templates/options` | tuỳ chọn CONFIG + danh sách ký hiệu DOCX |
| GET | `/api/admin/cv-templates/docx-sample` | link tải file Word mẫu Harvard |
| POST | `/api/admin/cv-templates` | tạo CONFIG (JSON) |
| POST | `/api/admin/cv-templates/docx` | tạo DOCX (multipart `file`, `name`) — kiểm tra + điền thử + PDF xem trước |
| PUT | `/api/admin/cv-templates/{id}` | sửa tên/cấu hình (CONFIG) |
| PUT | `/api/admin/cv-templates/{id}/docx` | thay file Word (kiểm tra như khi tạo) |
| PATCH | `/api/admin/cv-templates/{id}/status` | mẫu mặc định không ẩn được (409) |
| POST | `/api/admin/cv-templates/{id}/default` | đặt mặc định (1 transaction) |
| DELETE | `/api/admin/cv-templates/{id}` | 409 nếu đang dùng hoặc là mặc định; xoá file R2 sau khi xoá DB |
| POST | `/api/admin/cv-templates/preview` | CONFIG chưa lưu + dữ liệu mẫu → `text/html` |
| GET | `/api/admin/cv-templates/{id}/preview-pdf` | link ký tạm PDF xem trước |

Ứng viên — quyền `cv:manage-own`:

| Method | Path | Ghi chú |
|---|---|---|
| GET | `/api/cv-templates` | `ACTIVE`, mặc định đứng đầu, có `type`, `thumbnailUrl` |
| POST | `/api/cvs/preview` | `{templateId, title, profile}` chưa lưu → CONFIG: `text/html`; DOCX: `BaseResponse<FileLinkDto>` (PDF) |
| PUT | `/api/cvs/documents/{id}/template` | `{templateId}` |
| POST | `/api/cvs/documents/{id}/pdf` | sinh PDF từ dữ liệu đã lưu → `BaseResponse<FileLinkDto>` |

Thay đổi: `POST /api/cvs/documents/blank` nhận `templateId`; `PUT /api/cvs` sinh lại PDF cho CV form có mẫu (lỗi → vẫn lưu,
trả `pdfError`); tải file CV trả PDF đã sinh khi không có file gốc. HTML xem trước có header
`Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; font-src data:`. Gateway: thêm
`/api/admin/cv-templates/**`, `/api/cv-templates/**`. DTO mới viết dạng class Lombok.

## Frontend

- `cvTemplatesApi` (admin + ứng viên); bỏ mock mẫu CV trong `adminMock.ts`.
- AD06: danh sách có cột Loại (Cấu hình / Word), ảnh thu nhỏ, số CV dùng. Nút "Tạo mẫu" → chọn loại:
  - Cấu hình: form tuỳ chọn + sắp xếp mục + xem trước iframe (cập nhật khi đổi).
  - Word: tải file mẫu + link hướng dẫn ký hiệu, ô tải `.docx`, hiện lỗi ký hiệu nếu có, xem PDF điền thử, nút Lưu.
  - Ẩn/hiện, đặt mặc định, xoá (vô hiệu khi đang dùng, tooltip "Đang có N CV dùng, chỉ có thể ẩn").
- C02: "Tạo CV từ đầu" → hộp chọn mẫu (ảnh thu nhỏ) → `/candidate/cv/edit?new=1&templateId=`; "Tải file" bật cho CV form có PDF.
- C04: ô "Mẫu CV" là danh sách mẫu thật; xem trước: CONFIG = iframe HTML (debounce 600ms, huỷ request cũ),
  DOCX = nút "Cập nhật xem trước" (PDF); "Xem trước PDF" hoạt động; thêm ô "Địa điểm" cho học vấn/kinh nghiệm.

## Hạ tầng

- `docker-compose.yml`: service `gotenberg` (mạng nội bộ, không publish cổng ra ngoài; dev publish `127.0.0.1:3100`),
  recruitment-service thêm `GOTENBERG_URL`. Không có Gotenberg: mẫu DOCX báo "Chuyển đổi chưa sẵn sàng", mẫu CONFIG vẫn chạy.
- Tài liệu: `docs/CV_TEMPLATE_DOCX.md` (cách làm mẫu Word, bảng ký hiệu, font khuyên dùng, ví dụ Harvard).

## Kiểm chứng

- Unit: validate mẫu CONFIG (tên trùng, mục sai, tuỳ chọn ngoài bảng); quy tắc mặc định/ẩn/xoá; quyền; escape (`<script>` trong
  tên công ty hiện nguyên văn); DOCX: file sai đuôi/macro/quá lớn, ký hiệu không hỗ trợ, khối lặp rỗng bị ẩn.
- Render: snapshot HTML 2 layout + Harvard; PDF thật có tiếng Việt → PDFBox đọc lại text, nhiều trang khi dài; DOCX điền thử
  → Gotenberg (Testcontainers nếu có Docker, không thì bỏ qua có ghi chú).
- `mvn -pl recruitment-service,identity-service -am test` (JDK 21); FE lint + build; chạy thật theo kịch bản e2e.

## Rủi ro

| Rủi ro | Xử lý |
|---|---|
| OpenHTMLtoPDF xung đột `pdfbox 3` | Spike T001; dự phòng Flying Saucer |
| Cú pháp poi-tl cho khối lặp lồng nhau (mô tả nhiều dòng trong mỗi kinh nghiệm) | Spike T002; nếu khó, `description` thành 1 chuỗi xuống dòng |
| Word → PDF lệch bố cục, thiếu font | LibreOffice của Gotenberg; hướng dẫn chỉ dùng font có sẵn; luôn xem PDF điền thử trước khi lưu |
| Gotenberg nặng (~1GB image), chậm 1–3s | Chỉ dùng cho mẫu DOCX; xem trước DOCX theo nút bấm, không theo từng phím |
| File Word chứa link/ảnh ngoài | Gotenberg không có mạng ra ngoài; chặn `.docm` |
