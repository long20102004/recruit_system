# 008 · Lưu file trên Cloudflare R2

Hiện recruitment-service ghi mọi file xuống ổ đĩa (`app.upload.path`, mặc định `./uploads`) và lưu
**đường dẫn tuyệt đối** vào DB. Khi đổi máy, chạy Docker khác thư mục hay scale nhiều instance thì
file không đọc được. Logo/ảnh bìa công ty được ghi xuống đĩa nhưng chỉ lưu tên file, nên không hiển thị được.

Mục tiêu: mọi file (CV PDF, giấy phép công ty, logo, ảnh bìa) lưu trên **Cloudflare R2**; DB chỉ lưu object key.

Ngoài phạm vi:
- Avatar người dùng (identity-service chưa có tính năng upload).
- File của interview-service (chưa có code lưu file).
- Logo/ảnh bìa đã tải trước đây: DB không có đường dẫn nên không migrate được, người dùng tải lại.
- Hiển thị logo trên các màn khác ngoài trang hồ sơ công ty của nhà tuyển dụng và trang công ty công khai.

## Quyết định đã chốt (2026-11-27)

| Câu hỏi | Chọn |
|---|---|
| Truy cập CV PDF, giấy phép | Bucket **private**, backend kiểm tra quyền rồi trả **presigned URL** ngắn hạn |
| Logo, ảnh bìa | Bucket **public** (r2.dev hoặc custom domain), trả URL cố định |
| Chạy local không có R2 | **Chỉ dùng R2**, mọi môi trường cần cấu hình R2 (test đơn vị mock storage) |
| File cũ | **Script migrate** file local lên R2 và đổi giá trị DB sang object key |

Vì R2 bật public theo **cả bucket**, cần 2 bucket: private (CV, giấy phép) và public (ảnh).

## User stories

- **US1. Lưu CV PDF lên R2.** Ứng viên tải CV (luồng cũ và thêm CV mới), file nằm ở bucket private.
  Ứng viên tải CV của mình, nhà tuyển dụng tải CV trong đơn ứng tuyển qua URL ký tạm.
- **US2. Giấy phép công ty.** Nhà tuyển dụng tải giấy phép lên bucket private; admin xem qua URL ký tạm.
- **US3. Logo, ảnh bìa.** Nhà tuyển dụng tải logo/ảnh bìa lên bucket public; trang hồ sơ công ty
  (nhà tuyển dụng) và trang công ty công khai hiển thị ảnh.
- **US4. Migrate.** Một lệnh chuyển file CV và giấy phép đang lưu local lên R2 và cập nhật DB.

## Yêu cầu

- FR-001 Không còn ghi file xuống đĩa trong recruitment-service; DB lưu object key, không lưu đường dẫn máy.
- FR-002 Presigned URL hết hạn sau thời gian cấu hình (mặc định 5 phút), có `Content-Disposition`
  để trình duyệt tải về đúng tên file gốc.
- FR-003 Quyền truy cập giữ nguyên như hiện tại: ứng viên chỉ lấy CV của mình; nhà tuyển dụng chỉ lấy
  CV trong đơn ứng tuyển vào job của mình (`ensureCanAccess`); admin lấy giấy phép.
- FR-004 Xoá CV thì xoá object trên R2 (lỗi xoá chỉ ghi log, không chặn thao tác).
- FR-005 Ảnh chỉ nhận `image/png`, `image/jpeg`, `image/webp`, tối đa 5MB; CV và giấy phép giữ giới hạn hiện tại.
- FR-006 Secret R2 (access key, secret key) chỉ nằm trong biến môi trường, không commit; không log URL ký.
- FR-007 Thiếu cấu hình R2 thì service báo lỗi rõ khi khởi động.
- FR-008 Migrate chạy được nhiều lần (bỏ qua bản ghi đã là object key), báo số file đã chuyển / thiếu.

## Thay đổi contract

Ba endpoint tải file đổi từ trả **nội dung file** sang trả **link ký tạm** (frontend là consumer duy nhất, sửa cùng):
- `GET /api/cvs/documents/{id}/file`
- `GET /api/applications/{id}/cv-file`
- `GET /api/admin/companies/{id}/license`

Trả `BaseResponse<FileLinkDto{url, expiresAt}>`. Hồ sơ công ty thêm `logoUrl`, `coverUrl`.
