# 011 · Mẫu CV: admin tạo nhiều mẫu, ứng viên tạo CV từ mẫu (AD06, C02, C04)

Nguồn: `docs/MISSING_FEATURES.md` mục 14 (mẫu CV) và F1-04 (tạo CV từ form). Hiện AD06 chạy mock
(`adminMock.ts`); C04 (spec 010) có ô "Mẫu CV" và "Xem trước PDF" ở trạng thái "Sắp có"; CV tạo từ form không có file.

Mục tiêu: admin tạo được **nhiều kiểu mẫu** (Harvard, hiện đại 2 cột, tối giản ATS, mẫu Word tải trên mạng…);
ứng viên điền form và xuất CV PDF theo mẫu.

## Quyết định đã chốt (2026-11-27)

| Câu hỏi | Chọn |
|---|---|
| Cách admin tạo mẫu | **Hai loại mẫu**: (A) **cấu hình** trên AD06, bộ dựng có sẵn, tuỳ chọn trình bày mở rộng (đủ để làm Harvard); (B) **import file Word `.docx`** có ký hiệu điền chỗ, cho mọi kiểu khác |
| Import PDF | **Không**: PDF không mang cấu trúc/chỗ điền; AcroForm cố định số ô, không tự sang trang |
| Import HTML | Ngoài phạm vi đợt này (rủi ro bảo mật, admin cần biết HTML) |
| Sinh PDF | **Server sinh, lưu R2 private**, tải như CV upload |
| Xoá mẫu đang dùng | **Chặn xoá, chỉ cho ẩn** |
| "Người tham chiếu" | **Bỏ** |
| Địa điểm (Harvard) | **Thêm `location` tuỳ chọn** cho học vấn và kinh nghiệm trong hồ sơ CV; AI trích xuất để trống |

Ngoài phạm vi: import HTML/PDF, trình kéo thả bố cục, ảnh chân dung, CV đa ngôn ngữ, "Đang tìm việc", tự lưu nháp.

## User stories

- **US1. Admin tạo mẫu cấu hình (AD06).** Chọn bố cục, font, màu, căn lề phần đầu, kiểu tiêu đề mục, vị trí thời gian,
  độ dày đặc, lề trang, các mục và thứ tự; xem trước với dữ liệu mẫu; lưu, ẩn/hiện, đặt mặc định, xoá mẫu chưa dùng.
- **US2. Admin import mẫu Word (AD06).** Tải file `.docx` mẫu kèm hướng dẫn ký hiệu, thiết kế trong Word, tải lên;
  hệ thống kiểm tra ký hiệu, điền thử dữ liệu mẫu, cho xem PDF trước khi hiện cho ứng viên. Thay file mới cho mẫu đã có.
- **US3. Ứng viên chọn mẫu khi tạo CV từ đầu (C02).** Hộp chọn mẫu (ảnh thu nhỏ, mẫu mặc định chọn sẵn) → C04.
- **US4. Điền form, đổi mẫu, xem trước (C04).** Mẫu cấu hình: xem trước HTML cập nhật khi gõ. Mẫu Word: xem trước PDF khi
  bấm "Cập nhật xem trước" (chuyển đổi mất 1–3 giây).
- **US5. Xuất PDF.** "Xem trước PDF" sinh PDF từ dữ liệu đã lưu; lưu CV form thì sinh lại PDF; nhà tuyển dụng tải được.

## Yêu cầu

- FR-001 Mẫu có: tên (1–80, không trùng), loại `CONFIG`/`DOCX`, trạng thái `ACTIVE`/`HIDDEN`, cờ mặc định, ảnh thu nhỏ.
- FR-002 Mẫu `CONFIG`: bố cục `ONE_COLUMN`/`TWO_COLUMN`; font (sans: Be Vietnam Pro, Inter; serif: Tinos, EB Garamond,
  Noto Serif — đều có tiếng Việt); màu nhấn (bảng màu, có "Đen, không nhấn"); nền; căn phần đầu `LEFT`/`CENTER`;
  tiêu đề mục `UPPERCASE_RULE`/`ACCENT`/`PLAIN`; thời gian `RIGHT_INLINE`/`BELOW`; độ dày `COMPACT`/`NORMAL`;
  lề trang; mục có thứ tự (≥ 1) trong: `info`, `objective`, `education`, `experience`, `projects`, `skills`,
  `certificates`, `languages`, `honours`.
- FR-003 Mẫu `DOCX`: file ≤ 2MB, chỉ `.docx` (không `.docm`/macro); chỉ chấp nhận ký hiệu trong danh sách hỗ trợ (báo rõ
  ký hiệu sai và vị trí); phải điền thử + chuyển PDF thành công mới lưu được; không tải tài nguyên ngoài khi chuyển đổi.
- FR-004 Đúng một mẫu mặc định; mẫu mặc định không ẩn/xoá được. Xoá mẫu có CV dùng → 409.
- FR-005 Mẫu ẩn: ứng viên mới không chọn được; CV đang dùng vẫn xuất đúng. Sửa mẫu áp dụng từ lần xuất PDF kế tiếp.
- FR-006 Ứng viên chỉ thấy mẫu `ACTIVE`, chỉ gán mẫu cho CV của mình.
- FR-007 Dữ liệu ứng viên luôn được escape (HTML) / chèn dạng văn bản (DOCX); xem trước HTML trong iframe sandbox.
- FR-008 PDF A4, tiếng Việt đúng, tự sang trang; chữ chọn/tìm được (ATS đọc được).
- FR-009 CV upload: tải file trả file gốc; CV form: trả PDF đã sinh. Sinh PDF lỗi không mất dữ liệu đã lưu.
- FR-010 Mẫu không ảnh hưởng matching. Trường `location` không ảnh hưởng AI trích xuất và cvmatch.
- FR-011 Có sẵn: 4 mẫu cấu hình (Harvard — mặc định, Hiện đại 2 cột, Tối giản ATS, Cổ điển) và 1 file Word mẫu Harvard
  để admin tải về làm theo.

## Thay đổi contract

- Mới: `/api/admin/cv-templates/**` (quyền mới `cv-template:manage`), `/api/cv-templates`, `/api/cvs/preview`,
  `/api/cvs/documents/{id}/template`, `/api/cvs/documents/{id}/pdf` — chi tiết trong plan.
- `CandidateProfileDto`: `education[].location`, `experience[].location` (tuỳ chọn, thêm mới, tương thích ngược).
- `CvDocumentDto`, `CvFormDto` thêm `templateId`, `hasGeneratedPdf`.
- Tải file CV (ứng viên, nhà tuyển dụng): không có file gốc thì trả PDF đã sinh (trước: 404).
- AD06: bỏ "Người tham chiếu"; màu lưu mã hex thay cho CSS token; thêm loại mẫu Word.
- Hạ tầng: thêm container **Gotenberg** (chuyển DOCX → PDF) trong docker-compose.
