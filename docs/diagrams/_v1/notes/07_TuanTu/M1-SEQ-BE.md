# M1-SEQ-BE — Biểu đồ tuần tự Backend

- **Tên:** Biểu đồ tuần tự - Đăng ký, đăng nhập, chọn vai trò (Backend)
- **Nguồn thực thi:** `identity-service` và `JwtService` dùng chung. Kiến trúc microservices theo source.
- **Phạm vi:** Luồng đăng ký, chọn vai trò và các ngoại lệ 409/400. Login không mở rộng thành luồng riêng trong giới hạn biểu đồ; endpoint có trong lớp đã đối chiếu.

## Kịch bản (đánh số khớp seq)

1. Frontend gửi `POST /api/auth/register` với `request`.
2. `AuthController` gọi `AuthService.register(request)`.
3. `AuthService` kiểm tra email bằng `UserRepository.existsByEmailIgnoreCase(request.email())` (nhánh alt).
4. Repository trả `true`.
5. Backend trả lỗi xung đột đăng ký (409) do email đã tồn tại.
6. Ở nhánh email chưa tồn tại, service kiểm tra email bằng cùng operation.
7. Repository trả `false`; source tiếp tục chuẩn hóa email, tạo User mặc định CANDIDATE/roleChosen=false và lưu.
8. Service yêu cầu `JwtService.generateToken(user.getId(), user.getEmail(), user.getRole())`.
9. `JwtService` trả token.
10. Service trả `AuthDtos.AuthResponse`.
11. Controller trả response đăng ký cho client.
12. Client gửi `POST /api/auth/role` với request chọn role.
13. Controller gọi `AuthService.chooseRole(request)`.
14. Với role hợp lệ và chưa chọn, service xác thực principal, truy xuất/cập nhật/lưu User rồi gọi `generateToken(...)`.
15. `JwtService` trả token mới.
16. Service trả `AuthDtos.AuthResponse`.
17. Controller trả response chọn vai trò.
18. Nếu role không phải CANDIDATE/RECRUITER hoặc role đã được chọn, service phát sinh 400/409 thay vì trả response thành công.
19. Controller boundary trả lỗi HTTP tương ứng cho client.

## Bảng truy vết message → nguồn

| Seq | Message | Nguồn |
|---:|---|---|
| 1 | POST register | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:21-23` |
| 2 | `register(request)` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:21-23` |
| 3 | `existsByEmailIgnoreCase` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28-31` |
| 4 | Return true | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:29-30` |
| 5 | Return conflict | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:29-31` |
| 6 | `existsByEmailIgnoreCase` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28-31` |
| 7 | Return false | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:29-42` |
| 8 | `generateToken` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:44` |
| 9 | Return token | `source/recruit_system/backend/common/src/main/java/recruit/demo/security/JwtService.java:25-35` |
| 10 | Return AuthResponse | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:45-46` |
| 11 | HTTP response register | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:21-23` |
| 12 | POST role | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:31-33` |
| 13 | `chooseRole(request)` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:31-33` |
| 14 | `generateToken` trên nhánh hợp lệ | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:49-65` |
| 15 | Return token | `source/recruit_system/backend/common/src/main/java/recruit/demo/security/JwtService.java:25-35` |
| 16 | Return AuthResponse | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:64-66` |
| 17 | HTTP response role | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:31-33` |
| 18 | Return lỗi 400/409 | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:49-58` |
| 19 | HTTP lỗi role | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:31-33` |

## Điểm lệch so với M1-ACT

- Activity mô tả đầy đủ frontend, các lựa chọn login/register, điều hướng, JWT filter và provisioning profile của `recruitment-service`. Sequence này giới hạn Backend identity-service, nên chỉ biểu diễn đăng ký/chọn vai trò; không đưa các bước UI hay profile provisioning sang lifeline của service khác.
- ACT có ngoại lệ login sai thông tin (401), nhưng không thể biểu diễn đủ chính xác trong constraint lớp hiện tại: `AuthService.login` ủy thác `AuthenticationManager.authenticate`, operation này không có trong `M1-CLS-BE.json`. Không tự tạo lifeline/operation thiếu.
- Các thao tác lưu/tìm User và mã hóa mật khẩu có trong source nhưng thiếu operation tương ứng trong CLS, nên lược khỏi các message và ghi trong `open_questions` của spec. Không sửa biểu đồ lớp theo phạm vi task.
- Không có tài liệu M1 trong `docs/Module3_Interview_Flow.md`; tài liệu đó mô tả phỏng vấn (M4). Báo cáo PDF v6 không có trên đĩa như đã nêu trong task; kiến trúc sử dụng source microservices.
