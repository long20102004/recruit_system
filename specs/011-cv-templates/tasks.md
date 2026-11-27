# Tasks · 011 Mẫu CV

## Phase 0 · Spike
- [x] T001 OpenHTMLtoPDF (fork, pdfbox 3) cùng `pdfbox 3.0.5`: PDF A4 tiếng Việt từ XHTML + font nhúng
- [x] T002 poi-tl: điền file Word mẫu Harvard (ký hiệu đơn, khối lặp lồng nhau, khối rỗng bị ẩn) → Gotenberg → PDF; chốt cú pháp

## Phase 1 · Dữ liệu + render (recruitment-service)
- [x] T003 `V13__cv_templates.sql` (bảng, cột `cv_documents`, seed 4 mẫu CONFIG); entity, repository; `CvTemplateOptions`
- [x] T004 `location` cho học vấn/kinh nghiệm trong `CandidateProfileDto` (+ test tương thích JSON cũ)
- [x] T005 `CvHtmlRenderer` (Thymeleaf, 2 layout, tuỳ chọn trình bày) + `HtmlPdfRenderer`; font TTF; test snapshot + PDF đọc lại text
- [x] T006 `CvDocxRenderer` (poi-tl) + `GotenbergClient` + `DocxTemplateValidator`; `CvRenderService` chọn nhánh; test

## Phase 2 · API admin + hạ tầng
- [x] T007 identity `V9__cv_template_permission.sql` (`cv-template:manage` cho ADMIN); `docs/RBAC.md`
- [x] T008 `AdminCvTemplateController`: CRUD CONFIG, tạo/thay DOCX, trạng thái, mặc định, xoá chặn khi dùng, xem trước, ảnh thu nhỏ, file mẫu
- [x] T009 Gateway route; `docker-compose.yml` service `gotenberg` + `GOTENBERG_URL`; `.env.microservices.example`
- [x] T010 `docs/CV_TEMPLATE_DOCX.md` + `resources/cv-templates/harvard-sample.docx`

## Phase 3 · API ứng viên
- [x] T011 `GET /api/cv-templates`, `POST /api/cvs/preview` (HTML / PDF theo loại, CSP), `PUT /api/cvs/documents/{id}/template`
- [x] T012 `POST /api/cvs/documents/{id}/pdf`; `confirm` sinh lại PDF cho CV form có mẫu; `createBlank` nhận `templateId`
- [x] T013 Tải file (ứng viên + nhà tuyển dụng) dùng PDF đã sinh khi không có file gốc; DTO `templateId`, `hasGeneratedPdf`; test

## Phase 4 · Frontend [P] (theo contract trong plan, sau T008/T011)
- [x] T014 `cvTemplatesApi`; bỏ mock mẫu CV; type `location`, `normalizeProfile`/`cleanProfile`, ô Địa điểm ở form hồ sơ
- [x] T015 AD06: danh sách (loại, ảnh thu nhỏ, số CV dùng); tạo/sửa mẫu cấu hình + xem trước; import Word + lỗi ký hiệu + PDF điền thử
- [x] T016 C02: hộp chọn mẫu cho "Tạo CV từ đầu"; bật "Tải file" cho CV form có PDF
- [x] T017 C04: chọn mẫu thật, xem trước HTML (CONFIG) / PDF theo nút (DOCX), "Xem trước PDF" hoạt động

## Phase 5 · Kiểm chứng
- [x] T018 `mvn test` (recruitment, identity), FE lint + build, review diff
- [ ] T019 Chạy thật: admin tạo mẫu cấu hình + import Word Harvard, ẩn/xoá; ứng viên tạo CV từ từng loại mẫu, đổi mẫu, xuất PDF;
      nhà tuyển dụng tải PDF; cập nhật `docs/KICH_BAN_CHAY_FULL_LUONG.md`
