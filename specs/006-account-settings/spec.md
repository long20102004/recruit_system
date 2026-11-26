# 006 · Hồ sơ cá nhân, đổi mật khẩu, cài đặt thông báo (màn C14)

Giao diện: design canvas `Profile.dc.html` (C14 · Hồ sơ & mật khẩu). Route FE: `/candidate/profile`. Mở bằng cách bấm tên hoặc avatar trên thanh điều hướng.

Ngoài phạm vi: ảnh đại diện, gửi thông báo thật. Hệ thống chưa có module thông báo nên mới chỉ lưu tuỳ chọn.

## User stories

- **US1. Cập nhật thông tin cá nhân.** Ứng viên sửa họ tên, số điện thoại, ngày sinh, giới tính. Email và vai trò chỉ hiển thị, không sửa được.
- **US2. Đổi mật khẩu.** Ứng viên nhập mật khẩu hiện tại, mật khẩu mới và nhập lại. Sau khi đổi, các thiết bị khác bị đăng xuất, phiên hiện tại vẫn dùng tiếp.
- **US3. Đặt mật khẩu lần đầu.** Tài khoản tạo bằng Google chưa có mật khẩu: đặt mật khẩu mới mà không cần mật khẩu cũ.
- **US4. Cài đặt thông báo.** Bật/tắt thông báo trong ứng dụng và qua email cho 5 loại: trạng thái đơn, lời mời phỏng vấn, job alert, lời mời công ty, AI xử lý CV xong.

## Yêu cầu

| Mã | Nội dung |
|---|---|
| FR-001 | `GET/PUT /api/account/profile`: họ tên bắt buộc, tối đa 100 ký tự; SĐT 8–20 ký tự gồm số, khoảng trắng, `.`, `-`, `+`; ngày sinh phải trước hôm nay; giới tính `MALE` / `FEMALE` / `OTHER` / null. Sau khi lưu, xoá cache user trong Redis. |
| FR-002 | `POST /api/account/password`: mật khẩu mới theo quy tắc đăng ký (8–100 ký tự, có chữ và số) và phải khác mật khẩu hiện tại. Sai mật khẩu hiện tại trả 400, mã `2009`, và được tính vào bộ đếm đăng nhập sai (Redis), đủ ngưỡng thì khoá tạm, mã `2004`. |
| FR-003 | Đổi mật khẩu thành công: cập nhật `sessions_valid_after` để vô hiệu các JWT cũ, trả về `AuthResponse` có token mới. |
| FR-004 | `users.password_set = false` cho tài khoản tạo mới qua Google. Khi cờ này false, đổi mật khẩu không cần `currentPassword`. Đặt xong, cờ chuyển thành true. |
| FR-005 | `GET/PUT /api/account/notifications`: luôn trả đủ 5 loại. Loại chưa cấu hình dùng giá trị mặc định: tất cả bật, riêng "AI xử lý CV xong" tắt email. PUT chỉ cập nhật các loại được gửi lên (upsert). |
| FR-006 | Mọi vai trò đã đăng nhập đều gọi được `/api/account/**`. Gateway định tuyến các đường dẫn này tới identity-service. |
| FR-007 | JSON sai kiểu (ví dụ enum lạ) trả 400 "Dữ liệu gửi lên không hợp lệ", không lộ chi tiết parser. Áp dụng cho mọi service qua `GlobalExceptionHandler`. |

## Dữ liệu

Migration `V7__account_settings.sql`:

- Bảng `users` thêm các cột `date_of_birth`, `gender`, `password_set`.
- Bảng mới `notification_preferences(user_id, type, in_app, email)`, khoá chính `(user_id, type)`, xoá theo user (cascade).
