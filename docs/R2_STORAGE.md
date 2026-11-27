# Lưu file trên Cloudflare R2

recruitment-service lưu mọi file lên Cloudflare R2 (spec: [specs/008-r2-storage](../specs/008-r2-storage/spec.md)).
DB chỉ lưu **object key**, không lưu đường dẫn trên máy.

| Loại file | Bucket | Cách truy cập |
|---|---|---|
| CV PDF của ứng viên | private | Backend kiểm tra quyền, trả **presigned URL** hết hạn sau 5 phút |
| Giấy phép kinh doanh công ty | private | Như trên (admin xem inline) |
| Logo, ảnh bìa công ty | public | URL công khai cố định `R2_PUBLIC_BASE_URL/<key>` |

Cần **2 bucket** vì R2 bật public theo cả bucket, không theo thư mục.

Object key:

```
private  cvs/{candidateId}/{cvId}/{uuid}.pdf
private  companies/{companyId}/license/{uuid}.{ext}
public   companies/{companyId}/logo/{uuid}.{ext}
public   companies/{companyId}/cover/{uuid}.{ext}
```

## 1. Tạo bucket và token (làm một lần)

Trên Cloudflare dashboard → **R2 Object Storage**:

1. **Create bucket** `hirelens-private`. Giữ nguyên mặc định (không bật public access).
2. **Create bucket** `hirelens`. Vào **Settings → Public access**:
   - Đồ án: bật **R2.dev subdomain**, copy URL dạng `https://pub-xxxx.r2.dev`.
   - Production: gắn **Custom domain** (vd `cdn.hirelens.vn`) thay cho r2.dev (r2.dev có giới hạn tốc độ).
3. **Manage R2 API Tokens → Create API token**:
   - Permissions: **Object Read & Write**.
   - Specify bucket(s): chọn đúng 2 bucket trên.
   - Lưu lại **Access Key ID**, **Secret Access Key** (chỉ hiện một lần) và **Account ID** (góc phải trang R2).

Không cần cấu hình CORS: trình duyệt chỉ mở link (thẻ `<a>`, `<img>`), không `fetch` trực tiếp từ R2.

## 2. Cấu hình

Thêm vào `.env` ở gốc repo (không commit file này):

```env
R2_ACCOUNT_ID=<account id>
R2_ACCESS_KEY_ID=<access key id>
R2_SECRET_ACCESS_KEY=<secret access key>
R2_PRIVATE_BUCKET=hirelens-private
R2_PUBLIC_BUCKET=hirelens
R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev
# R2_PRESIGN_TTL=5m
```

- Chạy bằng Docker: `docker-compose.yml` đã truyền các biến này vào `recruitment-service`.
- Chạy Java trực tiếp: export các biến trên trước khi chạy.

Thiếu biến bắt buộc thì recruitment-service **dừng ngay lúc khởi động** với lỗi `storage.r2.*`.
Mọi môi trường (kể cả máy dev) đều cần R2; mỗi người có thể dùng bucket riêng để không lẫn dữ liệu.

## 3. Chuyển file cũ lên R2 (một lần)

File tải lên trước đây nằm trong `./uploads` (hoặc volume `recruitment_uploads` khi chạy Docker),
DB lưu đường dẫn tuyệt đối. Để chuyển:

1. Đặt `STORAGE_MIGRATE_LOCAL=true` trong `.env`.
2. Khởi động lại recruitment-service (Docker: `docker compose up -d recruitment-service`).
3. Xem log: `Migrate file local -> R2 xong: chuyển N, thiếu file M, lỗi K`.
4. Đặt lại `STORAGE_MIGRATE_LOCAL=false`.

Phạm vi: CV PDF và giấy phép công ty. Logo/ảnh bìa cũ không có đường dẫn trong DB nên phải tải lại.
Chạy lại nhiều lần an toàn (bỏ qua bản ghi đã là object key). Bản ghi "thiếu file" vẫn giữ đường dẫn cũ;
khi tải, API báo file chưa được chuyển, người dùng tải lại CV là xong.

Sau khi migrate xong và kiểm tra ổn, có thể xoá thư mục `uploads` / volume `recruitment_uploads`.

## 4. Thay đổi API (frontend đã cập nhật)

Ba endpoint tải file trả **link ký tạm** thay vì nội dung file:

| Endpoint | Trả về |
|---|---|
| `GET /api/cvs/documents/{id}/file` | `BaseResponse<{url, expiresAt}>` |
| `GET /api/applications/{id}/cv-file` | `BaseResponse<{url, expiresAt}>` |
| `GET /api/admin/companies/{id}/license` | `BaseResponse<{url, expiresAt}>` |

`POST /api/recruiter/company/files?kind=logo|cover|license` ghi lên R2. Logo/ảnh bìa chỉ nhận PNG, JPEG,
WebP ≤ 5MB. Hồ sơ công ty trả thêm `logoUrl`, `coverUrl`.

## 5. Bảo mật

- Secret R2 chỉ nằm trong biến môi trường; không log URL ký hay nội dung file.
- Link ký tạm ai có cũng mở được cho tới khi hết hạn (5 phút), nên không gửi link qua kênh công khai.
- Bucket public chỉ chứa ảnh công ty, không đặt dữ liệu cá nhân vào đó.
