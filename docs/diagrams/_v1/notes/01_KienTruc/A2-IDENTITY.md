# A2-IDENTITY — Kiến trúc chiều ngang (MVC) của identity-service

- **Biểu đồ:** Package Diagram, `type = "package"`, tên: `Kiến trúc chiều ngang (MVC) - identity-service`.
- **Phạm vi:** identity-service và các DTO common được dùng trong luồng xác thực.
- **Nguồn chuẩn:** source code (DIAGRAM_RULES §0.1); PDF báo cáo không có trên đĩa, bỏ qua.
- **Cổng / CSDL:** `8081`, `hirelens_identity`; gateway định tuyến `/api/auth` (CLAUDE.md §3).
- **Giới hạn:** 3 package tầng; View 4 class, Controller 2 class, Model 4 class; tổng 12 phần tử, 10 quan hệ.

## Ánh xạ MVC và truy vết

| Tầng | Phần tử tiêu biểu | Vai trò / nguồn |
|---|---|---|
| View | `AuthDtos.LoginRequest`, `AuthDtos.RegisterRequest`, `AuthDtos.UserResponse`, `AuthDtos.AuthResponse` | DTO request/response trong `source/recruit_system/backend/common/src/main/java/recruit/demo/dto/AuthDtos.java:14,20,31,40` |
| Controller | `AuthController`, `InternalUserController` | API công khai và nội bộ; `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:12`; `.../InternalUserController.java:13` |
| Model | `AuthService`, `UserRepository`, `User`, `CustomUserDetailsService` | Nghiệp vụ, truy cập dữ liệu và tải principal; `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:20`; `.../repository/UserRepository.java:8`; `.../entity/User.java:17`; `.../security/CustomUserDetailsService.java:12` |

## Quan hệ thể hiện

- Package dependencies: `Controller → View`, `Controller → Model`, `Model → View` (DTO được controller/service dùng; hướng phụ thuộc phản ánh source), cùng quan hệ `Controller → common` và `Model → common` đã bỏ do giản lược common.
- Class relations giữ trong spec: `AuthController → AuthService`, `InternalUserController → UserRepository`, `AuthService → UserRepository`, `AuthService → AuthDtos.AuthResponse`, `AuthService → User`, `UserRepository → User`.
- `UserRepository` là Spring Data repository; `CustomUserDetailsService` dùng repository và triển khai `PrincipalLookup` nhưng hai chi tiết này không vẽ trong bản rút gọn.

## Phần lược bỏ

Các class/enum không còn trong hình được liệt kê đầy đủ trong `notes` của JSON dưới chuỗi `Lược bỏ: ...`. Các class common về bảo mật/exception/config, enum, DTO phụ và cấu hình identity bị lược để đạt giới hạn kích thước; không hàm ý chúng không tồn tại trong source.

## Mâu thuẫn / lưu ý nguồn

1. CLAUDE.md §3 mô tả mỗi service có package `dto` và `client`; identity-service thực tế không có hai package này. DTO dùng từ `backend/common`, và identity-service không gọi service khác.
2. DIAGRAM_RULES §1.2 nêu chiều phụ thuộc `View → Controller → Model`; source cho thấy controller và service phụ thuộc DTO, nên quan hệ thể hiện là `Controller → View` và `Model → View`. Bố cục vẫn theo tầng MVC.
3. Các bất nhất `User.updatedAt`/DDL và `User.phone`/DDL ghi ở ghi chú bản trước không ảnh hưởng biểu đồ package; xem source migration khi lập ERD.

## Open questions

Không còn câu hỏi mở cho phạm vi spec rút gọn này.
