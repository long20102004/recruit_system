# Research: Hoàn thiện luồng xác thực

## R1. Vô hiệu JWT khi khoá tài khoản / đặt lại mật khẩu

- **Decision**: Thêm cột `users.sessions_valid_after`. `JwtAuthenticationFilter` từ chối token có `iat` (giây) nhỏ hơn mốc này. Mốc đi kèm bản tóm tắt người dùng mà mọi service đã đọc ở mỗi request.
- **Rationale**: Mọi service đã nạp người dùng ở mỗi request (`PrincipalLookup`), nên thêm một trường là đủ, không cần danh sách đen theo từng token. Dữ liệu bền (MySQL), Redis chỉ là cache.
- **Alternatives**: Blacklist `jti` trong Redis (phải lưu từng token, cần thêm `jti`); rút ngắn hạn token + refresh token (ngoài phạm vi).
- **Lưu ý**: `iat` làm tròn giây, nên token cấp trong cùng giây trước mốc vẫn qua. Cửa sổ dưới 1 giây, chấp nhận.

## R2. Cache tóm tắt người dùng (Redis)

- **Decision**: Redis hash `auth:user:{id}` (id, email, fullName, phone, role, status, sessionsValidAfter), TTL 60 giây (`app.identity.cache-ttl`). `RemotePrincipalLookup` đọc cache, trượt thì gọi `/internal/users/{id}` rồi ghi cache. identity-service xoá key khi khoá / mở khoá, đặt lại mật khẩu, chọn vai trò, sửa họ tên / SĐT.
- **Rationale**: Khoá có hiệu lực ngay (xoá cache → lần đọc sau lấy trạng thái mới), giảm gọi identity (INF-05). Hash tránh phụ thuộc định dạng JSON giữa các service.
- **Alternatives**: Pub/sub để các service tự xoá cache cục bộ (phức tạp hơn); không cache (không đạt SC-006).
- **Khi Redis lỗi**: đọc thẳng identity (fail-open cho cache, vẫn đúng vì dữ liệu gốc ở identity). Timeout Redis 500ms nên request chậm thêm khoảng 1 giây khi Redis chết.
- **Rủi ro đua đã biết**: một request đọc identity ngay trước khi admin khoá rồi ghi cache ngay sau khi identity xoá key thì cache giữ trạng thái cũ tối đa bằng TTL. TTL 60 giây giới hạn trường hợp xấu nhất; E2E không gặp.

## R3. Đếm đăng nhập sai và khoá tạm

- **Decision**: `INCR auth:login:fail:{email}`, đặt `EXPIRE` 15 phút ở lần đầu. Đạt 5 → `SET auth:login:lock:{email} 1 EX 900` và xoá bộ đếm. Kiểm tra khoá trước khi so mật khẩu; trả 423 kèm `retryAfterSeconds` (TTL còn lại). Đăng nhập đúng → xoá bộ đếm.
- **Rationale**: Theo email chuẩn hoá nên không lộ email tồn tại; TTL tự gỡ khoá.
- **Khi Redis lỗi**: bỏ qua đếm, ghi log cảnh báo (fail-open), đăng nhập vẫn chạy (Edge Cases).
- **Alternatives**: Lưu số lần sai trong MySQL (không lộ được cho email không tồn tại, phải dọn dữ liệu).

## R4. Token dùng một lần

- **Decision**: 32 byte `SecureRandom`, Base64 URL. Lưu `auth:token:{purpose}:{sha256(token)}` → userId với TTL (verify 24h, reset 30 phút), kèm `auth:token:{purpose}:user:{userId}` → hash để huỷ token cũ khi cấp token mới. Tiêu thụ bằng `GETDEL` (nguyên tử, chống dùng hai lần). Giãn cách gửi: `SET auth:cooldown:{purpose}:{email} 1 NX EX 60`.
- **Rationale**: Không lưu token gốc (FR-020); TTL tự dọn; `GETDEL` cần Redis ≥ 6.2 (dùng 7).
- **Khi Redis lỗi**: trả 503 "tạm thời không khả dụng".

## R5. Kiểm tra mật khẩu và trạng thái khi đăng nhập

- **Decision**: AuthService tự tìm user và `passwordEncoder.matches`, chỉ khi đúng mật khẩu mới báo "chưa xác thực" / "bị khoá". Email không tồn tại vẫn chạy một lần so khớp BCrypt giả để thời gian phản hồi tương đương.
- **Rationale**: `DaoAuthenticationProvider` kiểm tra khoá *trước* mật khẩu và ném `LockedException` (hiện ra lỗi 500), làm lộ trạng thái tài khoản khi chưa biết mật khẩu.

## R6. Gửi mail

- **Decision**: `spring-boot-starter-mail` (`JavaMailSender`), mail văn bản tiếng Việt, timeout kết nối / đọc 5 giây. Lỗi gửi được bắt và ghi log (không log link). Dev dùng Mailpit (SMTP 1025, giao diện 8025).
- **Alternatives**: Gửi bất đồng bộ qua hàng đợi (để sau khi có RabbitMQ / notification-service).

## R7. Phân quyền API admin

- **Decision**: `SecurityUtils.requireRole(Role.ADMIN)` trong service, đúng convention hiện tại. Route gateway `^/api/admin/users` → identity (để `/api/admin/*` khác sau này đi service khác).

## R8. Mã lỗi

- **Decision**: dùng `BusinessException` + `ErrorCode` (body `{code, message, data}`), thêm: 2003 EMAIL_NOT_VERIFIED (403), 2004 LOGIN_TEMPORARILY_LOCKED (423), 2005 ACCOUNT_LOCKED (403), 2006 INVALID_LINK_TOKEN (400), 2007 CANNOT_LOCK_USER (400). FE đọc `code`.
