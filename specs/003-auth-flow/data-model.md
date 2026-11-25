# Data Model: Hoàn thiện luồng xác thực

## MySQL `hirelens_identity.users` (migration `V4__auth_flow.sql`)

| Cột mới | Kiểu | Ý nghĩa |
|---|---|---|
| `email_verified_at` | DATETIME NULL | NULL = chưa xác thực email. Migration đặt = `created_at` cho mọi user đã có (gồm seed) |
| `locked_reason` | VARCHAR(500) NULL | Lý do admin khoá |
| `locked_at` | DATETIME NULL | Thời điểm admin khoá |
| `sessions_valid_after` | DATETIME NULL | JWT có `iat` trước mốc này bị từ chối |

`status` giữ nguyên enum (`ACTIVE` / `INACTIVE` / `BANNED`); admin khoá = `BANNED`. Chưa xác thực email không dùng `INACTIVE` để không lẫn hai khái niệm.

### Chuyển trạng thái

```text
đăng ký ──► ACTIVE, email_verified_at = NULL ──(bấm link / đặt lại mật khẩu)──► ACTIVE, đã xác thực
ACTIVE ──(admin khoá: lý do, locked_at, sessions_valid_after = now)──► BANNED
BANNED ──(admin mở khoá: xoá lý do, locked_at)──► ACTIVE
đặt lại mật khẩu ──► sessions_valid_after = now, email_verified_at = now nếu NULL
```

Quy tắc: không khoá được chính mình hoặc user `ADMIN`; lý do bắt buộc, ≤ 500 ký tự.

## Redis (mọi key có TTL)

| Key | Giá trị | TTL | Dùng cho |
|---|---|---|---|
| `auth:login:fail:{email}` | số lần sai | 15 phút từ lần sai đầu | FR-006 |
| `auth:login:lock:{email}` | `1` | 15 phút | FR-007 |
| `auth:token:verify:{sha256}` | userId | 24 giờ | FR-002, FR-003 |
| `auth:token:reset:{sha256}` | userId | 30 phút | FR-013, FR-014 |
| `auth:token:{purpose}:user:{userId}` | sha256 hiện hành | như token | huỷ token cũ khi cấp mới |
| `auth:cooldown:{purpose}:{email}` | `1` | 60 giây | FR-004, FR-013 |
| `auth:user:{id}` (hash) | id, email, fullName, phone, role, status, sessionsValidAfter (epoch giây, rỗng nếu NULL) | 60 giây | FR-017, FR-018 |

`{email}` luôn là email đã `trim` + chữ thường.

## DTO dùng chung (`common`)

- `ServiceDtos.UserSnapshot` thêm `Long sessionsValidAfter` (epoch giây, có thể null). Thêm trường cuối nên JSON cũ vẫn đọc được.
- `UserPrincipal` thêm `sessionsValidAfter`; giữ constructor 6 tham số cũ (mặc định null) để không phải sửa test của module khác.
