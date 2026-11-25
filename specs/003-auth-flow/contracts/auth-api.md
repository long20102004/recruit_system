# Contract: Auth API (identity-service, qua gateway `:8080`)

Lỗi nghiệp vụ trả body `{ "code": number, "message": string, "data": object|null }`. Lỗi validation giữ dạng cũ `{ "message": string }` với HTTP 400.

## Thay đổi so với hiện tại

| Endpoint | Trước | Sau |
|---|---|---|
| `POST /api/auth/register` | 200 `{token, user}`, mật khẩu ≥ 6 | **200 `{email, message}`, không có token**; mật khẩu 8–100, có chữ và số |
| `POST /api/auth/login` | User bị khoá → 500 | Mã lỗi riêng (bảng dưới) |
| `GET /internal/users/{id}` | `UserSnapshot` 6 trường | thêm `sessionsValidAfter` (tương thích ngược) |

## Endpoint công khai (`/api/auth`, không cần JWT)

### `POST /api/auth/register`
Request `{ "email": "a@b.com", "password": "abc12345" }` → 200 `{ "email": "a@b.com", "message": "Đã gửi email xác thực…" }`.
Lỗi: 409 `2002` email đã đăng ký; 400 validation.

### `POST /api/auth/verify-email`
Request `{ "token": "<từ link>" }` → 200 `{ token, user }` (như login).
Lỗi: 400 `2006` link không hợp lệ / hết hạn; 403 `2005` tài khoản bị khoá; 503 Redis lỗi.

### `POST /api/auth/resend-verification`
Request `{ "email": "a@b.com" }` → 200 `{ "message": "Nếu email cần xác thực, bạn sẽ nhận được email mới." }` (luôn như vậy).

### `POST /api/auth/login`
Request `{ email, password }` → 200 `{ token, user }`.

| HTTP | code | Khi nào | data |
|---|---|---|---|
| 401 | 2001 | Sai email hoặc mật khẩu | null |
| 423 | 2004 | Đang khoá tạm (kiểm tra trước mật khẩu) | `{ "retryAfterSeconds": 840 }` |
| 403 | 2003 | Đúng mật khẩu, chưa xác thực email | `{ "email": "a@b.com" }` |
| 403 | 2005 | Đúng mật khẩu, bị admin khoá | null |

### `POST /api/auth/forgot-password`
Request `{ email }` → 200 `{ "message": "Nếu email tồn tại, bạn sẽ nhận được link đặt lại mật khẩu." }` (luôn như vậy).

### `POST /api/auth/reset-password`
Request `{ "token": "...", "newPassword": "abc12345" }` → 200 `{ "message": "Đã đặt lại mật khẩu." }`.
Lỗi: 400 `2006`; 400 validation; 503 Redis lỗi.

## Endpoint cần JWT (không đổi)

`GET /api/auth/me`, `POST /api/auth/role`. Token có `iat` trước `sessionsValidAfter` của user → 401 ở mọi service.

## Endpoint admin (`/api/admin/users`, JWT role ADMIN, khác → 403)

### `GET /api/admin/users?q=&status=&page=0&size=20`
→ 200 `PageResponse<AdminUserDto>`; `AdminUserDto = { id, fullName, email, role, status, emailVerified, lockedReason, lockedAt, createdAt }`. `q` tìm trong email / họ tên; `status` ∈ ACTIVE, INACTIVE, BANNED; `size` ≤ 100.

### `PATCH /api/admin/users/{id}/lock`
Request `{ "reason": "Spam tin tuyển dụng" }` (bắt buộc, ≤ 500) → 200 `AdminUserDto`.
Lỗi: 404 không có user; 400 `2007` tự khoá mình hoặc khoá ADMIN.

### `PATCH /api/admin/users/{id}/unlock`
→ 200 `AdminUserDto`. Mở khoá user không bị khoá: trả về như cũ (idempotent).

## Link trong email

- Xác thực: `{APP_FRONTEND_URL}/verify-email?token=<token>`
- Đặt lại: `{APP_FRONTEND_URL}/reset-password?token=<token>`
