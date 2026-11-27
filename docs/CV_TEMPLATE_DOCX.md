# Hướng dẫn tạo mẫu CV Word (`.docx`) cho Admin

Tài liệu này hướng dẫn cách soạn tệp `.docx` để tải lên làm mẫu CV hệ thống (màn hình **Quản trị → Mẫu CV**, quyền `cv-template:manage`, đặc tả [`specs/011-cv-templates`](../specs/011-cv-templates/spec.md)).

Khi ứng viên sử dụng mẫu Word, `recruitment-service` sẽ điền dữ liệu hồ sơ vào các ký hiệu `{{...}}` (qua `poi-tl`), sau đó gửi tệp `.docx` sang **Gotenberg** (LibreOffice) để xuất ra PDF và ảnh thu nhỏ trang đầu.

---

## 1. Yêu cầu đối với tệp `.docx`

| Quy định | Chi tiết |
|---|---|
| **Định dạng** | Chỉ chấp nhận tệp Word `.docx` (Office Open XML). Không nhận `.doc`, `.docm` (có macro) hoặc tệp đổi đuôi giả. |
| **Dung lượng tối đa** | **2 MB**. |
| **Tài nguyên ngoài** | **Không** chèn ảnh liên kết từ URL ngoài hoặc liên kết tải tài nguyên từ Internet. Chỉ dùng văn bản, bảng, đường kẻ và định dạng chuẩn của Word. |
| **Ký hiệu hợp lệ** | Mọi thẻ `{{...}}` trong tài liệu phải thuộc danh sách ký hiệu hệ thống hỗ trợ bên dưới. Nếu có thẻ lạ hoặc gõ sai chính tả, API sẽ từ chối (HTTP `400`) và trả về danh sách ký hiệu không hợp lệ. |
| **Cách gõ thẻ trong Word** | Gõ liền mạch toàn bộ thẻ (ví dụ `{{full_name}}`), không bôi đen định dạng một nửa thẻ. Nếu chỉnh sửa nhiều lần khiến Word tách thẻ thành nhiều đoạn XML ngầm, hãy xoá thẻ đó và gõ lại nguyên vẹn hoặc dán dạng văn bản thuần (*Keep Text Only*). |

> [!TIP]
> Có thể tải tệp mẫu Harvard chuẩn trực tiếp trên giao diện tạo mẫu Word (hoặc qua `GET /api/admin/cv-templates/docx-sample`) để chỉnh sửa lại thay vì tự tạo từ đầu.

---

## 2. Bảng ký hiệu hỗ trợ

Tất cả ký hiệu khớp với hằng số `CvTemplateOptions.DOCX_PLACEHOLDERS` trong `recruitment-service`.

### 2.1. Trường đơn (cấp gốc)

Đặt trực tiếp ở bất kỳ vị trí nào trong tài liệu (đoạn văn, ô bảng, đầu trang/chân trang). Nếu ứng viên chưa nhập, hệ thống điền chuỗi rỗng.

| Ký hiệu | Ý nghĩa |
|---|---|
| `{{full_name}}` | Họ và tên ứng viên |
| `{{title}}` | Tiêu đề CV (vị trí ứng tuyển / chức danh) |
| `{{email}}` | Email liên hệ |
| `{{phone}}` | Số điện thoại |
| `{{github}}` | Đường dẫn GitHub |
| `{{objective}}` | Mục tiêu nghề nghiệp |
| `{{skills_text}}` | Toàn bộ kỹ năng nối với nhau bằng dấu phẩy (ví dụ: `Java, Spring Boot, MySQL`) |
| `{{certificates_text}}` | Danh sách chứng chỉ nối theo từng dòng |
| `{{honours_text}}` | Danh sách giải thưởng & hoạt động nối theo từng dòng |

### 2.2. Khối lặp (tự ẩn khi rỗng)

Khối lặp mở bằng `{{?tên_khối}}` và đóng bằng `{{/tên_khối}}`.
- Hệ thống lặp phần nội dung nằm giữa cặp thẻ cho từng phần tử trong hồ sơ.
- **Nếu ứng viên để trống mục đó** (danh sách rỗng), **toàn bộ khối từ thẻ mở đến thẻ đóng sẽ tự động bị ẩn**. Nhờ vậy có thể đặt cả tiêu đề mục (ví dụ `KINH NGHIỆM LÀM VIỆC`) vào bên trong khối `{{?experience}}...{{/experience}}` nếu muốn ẩn cả tiêu đề khi chưa có dữ liệu, hoặc chỉ bọc phần danh sách mục con.

| Khối lặp | Các trường dùng được bên trong | Ý nghĩa |
|---|---|---|
| `{{?experience}}...{{/experience}}` | `{{job_title}}`, `{{company}}`, `{{location}}`, `{{start_date}}`, `{{end_date}}`, `{{description}}` | Kinh nghiệm làm việc (chức danh, công ty, địa điểm, ngày bắt đầu, ngày kết thúc, mô tả) |
| `{{?education}}...{{/education}}` | `{{school}}`, `{{major}}`, `{{location}}`, `{{start_year}}`, `{{end_year}}`, `{{gpa}}` | Học vấn (trường, chuyên ngành, địa điểm, năm bắt đầu, năm kết thúc, GPA) |
| `{{?projects}}...{{/projects}}` | `{{name}}`, `{{role}}`, `{{team_size}}`, `{{start_date}}`, `{{end_date}}`, `{{github_url}}`, `{{tech_stack}}`, `{{description}}` | Dự án cá nhân (tên dự án, vai trò, quy mô nhóm, thời gian, link GitHub, công nghệ, mô tả) |
| `{{?languages}}...{{/languages}}` | `{{language}}`, `{{note}}` | Ngoại ngữ (tên ngoại ngữ, ghi chú / chứng chỉ đạt được) |

### 2.3. Danh sách lặp dạng chuỗi đơn

Dùng khi muốn trình bày từng kỹ năng / chứng chỉ / giải thưởng thành từng dòng hoặc từng gạch đầu dòng riêng thay vì dùng `{{skills_text}}`, `{{certificates_text}}`, `{{honours_text}}`.

| Cú pháp | Ý nghĩa |
|---|---|
| `{{?skills}}{{value}}{{/skills}}` | Danh sách lặp từng kỹ năng (`{{value}}` là tên kỹ năng) |
| `{{?certificates}}{{value}}{{/certificates}}` | Danh sách lặp từng chứng chỉ (`{{value}}` là tên chứng chỉ) |
| `{{?honours}}{{value}}{{/honours}}` | Danh sách lặp từng giải thưởng & hoạt động (`{{value}}` là nội dung mục) |

---

## 3. Font chữ khuyên dùng (có sẵn trong Gotenberg)

Gotenberg chạy LibreOffice trên Linux nên chỉ nhận đúng bộ font được cài sẵn trong container. Nếu tệp Word dùng font bản quyền của Windows/macOS (như *Times New Roman*, *Arial*, *Calibri*, *Cambria*), LibreOffice sẽ tự thay thế bằng font khác, dễ gây lệch khoảng cách dòng hoặc nhảy trang.

Hãy chọn một trong các font có sẵn và hỗ trợ tốt tiếng Việt sau:

| Font khuyên dùng | Nhóm | Tương đương với | Gợi ý sử dụng |
|---|---|---|---|
| **Liberation Serif** | Serif (có chân) | Times New Roman / Tinos | Mẫu cổ điển, Harvard, học thuật |
| **Liberation Sans** | Sans-serif (không chân) | Arial | Mẫu tối giản, chuẩn ATS |
| **Noto Sans** | Sans-serif | Hiện đại, tròn gọn | Mẫu hiện đại, hỗ trợ tiếng Việt đầy đủ |
| **Noto Serif** | Serif | Trang nhã, sắc nét | Mẫu chuyên nghiệp có điểm nhấn cổ điển |
| **Carlito** | Sans-serif | Calibri | Tương thích kích thước chữ Calibri |
| **Caladea** | Serif | Cambria | Tương thích kích thước chữ Cambria |

---

## 4. Ví dụ bố cục Harvard một cột

Dưới đây là cấu trúc văn bản gợi ý khi thiết kế tệp `.docx` phong cách **Harvard** (font `Liberation Serif`, cỡ chữ 10.5pt–11pt, tiêu đề mục in hoa kèm đường kẻ dưới đoạn *Bottom Border*):

```text
                        {{full_name}}
                        {{title}}
        {{email}}  |  {{phone}}  |  {{github}}
────────────────────────────────────────────────────────────────

MỤC TIÊU NGHỀ NGHIỆP
{{objective}}

HỌC VẤN
{{?education}}
{{school}} — {{location}}                       {{start_year}} – {{end_year}}
{{major}} | GPA: {{gpa}}
{{/education}}

KINH NGHIỆM LÀM VIỆC
{{?experience}}
{{job_title}} — {{company}} ({{location}})      {{start_date}} – {{end_date}}
{{description}}
{{/experience}}

DỰ ÁN CÁ NHÂN
{{?projects}}
{{name}} — {{role}} (Nhóm: {{team_size}})       {{start_date}} – {{end_date}}
Công nghệ: {{tech_stack}} | GitHub: {{github_url}}
{{description}}
{{/projects}}

KỸ NĂNG
{{skills_text}}

CHỨNG CHỈ
{{?certificates}}
• {{value}}
{{/certificates}}

NGOẠI NGỮ
{{?languages}}
• {{language}}: {{note}}
{{/languages}}

GIẢI THƯỞNG & HOẠT ĐỘNG
{{?honours}}
• {{value}}
{{/honours}}
```

> [!NOTE]
> Để căn phải phần thời gian (`{{start_date}} – {{end_date}}`) cùng hàng với tên trường/công ty trong Word, hãy đặt **Right Tab Stop** ở lề phải hoặc dùng bảng 2 cột không viền (cột trái rộng ~75%, cột phải rộng ~25% căn phải).

---

## 5. Quy trình kiểm tra trước khi lưu mẫu

1. Mở màn hình **Quản trị → Mẫu CV → Tạo mẫu → Mẫu Word (.docx)**.
2. Tải tệp `.docx` lên cùng tên mẫu (tối đa 80 ký tự, không trùng tên mẫu khác).
3. Hệ thống kiểm tra định dạng, dung lượng, macro, thẻ `{{...}}`, điền thử hồ sơ mẫu tổng hợp và gọi Gotenberg xuất PDF xem trước.
4. Kiểm tra kỹ PDF điền thử (căn lề, tiếng Việt, ngắt trang, ẩn khối rỗng) trước khi bật trạng thái **Hiển thị (ACTIVE)** cho ứng viên sử dụng.
