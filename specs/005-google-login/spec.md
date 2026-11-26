# Feature Specification: Đăng nhập bằng Google

**Branch**: `hocnv/google-login` · **Created**: 2026-11-26 · **Status**: Draft

**Input**: "Bổ sung thêm luồng đăng nhập bằng Google". Đã chốt: Google Sign-In trên FE (Google Identity Services, ID token) + backend xác minh; email trùng tài khoản mật khẩu thì tự liên kết; Client ID đặt qua biến môi trường, chưa có thì ẩn nút.

## User Stories

1. **(P1) Đăng nhập nhanh bằng Google.** Người dùng bấm "Đăng nhập bằng Google" ở trang đăng nhập / đăng ký, chọn tài khoản Google và vào hệ thống. Lần đầu (chưa có tài khoản) thì được tạo tài khoản đã xác thực email và chuyển tới màn chọn vai trò.
2. **(P1) Liên kết tài khoản sẵn có.** Email Google trùng tài khoản đăng ký bằng mật khẩu → đăng nhập vào đúng tài khoản đó; từ đó dùng được cả hai cách. Tài khoản chưa xác thực email được coi là đã xác thực.
3. **(P2) An toàn.** Token giả, hết hạn, cấp cho ứng dụng khác hoặc email Google chưa xác thực bị từ chối. Tài khoản bị admin khoá vẫn bị chặn.

## Functional Requirements

- **FR-001** `POST /api/auth/google {credential}` nhận ID token của Google Identity Services, trả `{token, user}` như đăng nhập thường (kèm permissions).
- **FR-002** Xác minh token: chữ ký theo JWKS của Google, `iss` ∈ {`accounts.google.com`, `https://accounts.google.com`}, `aud` chứa Client ID của hệ thống, `exp` còn hạn, `email_verified = true`.
- **FR-003** Tìm user theo `google_sub`; không có thì theo email (liên kết, lưu `google_sub`); không có thì tạo user mới: vai trò CANDIDATE chưa chọn (`role_chosen = false`), email đã xác thực, họ tên từ Google, mật khẩu ngẫu nhiên không dùng được (người dùng đặt mật khẩu qua "Quên mật khẩu" nếu cần).
- **FR-004** Tài khoản không ACTIVE → 403 `2005`; token không hợp lệ → 401 `2008`; chưa cấu hình Client ID → 503.
- **FR-005** FE hiện nút Google ở trang đăng nhập và đăng ký khi có `VITE_GOOGLE_CLIENT_ID`; sau đăng nhập điều hướng như đăng nhập thường (user mới → chọn vai trò).
- **FR-006** Không lưu ID token / thông tin Google ngoài `google_sub`, email, họ tên; không log token.

## Ngoài phạm vi

Đăng nhập Facebook / GitHub; huỷ liên kết Google; ảnh đại diện từ Google; OAuth2 redirect phía server.
