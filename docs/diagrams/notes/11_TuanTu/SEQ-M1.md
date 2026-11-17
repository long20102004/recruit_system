# SEQ-M1 — Biểu đồ tuần tự thiết kế: Đăng ký, đăng nhập và chọn vai trò

## Kịch bản chuẩn V3

1. Người dùng truy cập `/register`, nhập email và mật khẩu, nhấn nút tạo tài khoản.
2. `RegisterPage.tsx` thực hiện `onSubmit()`.
3. `RegisterPage.tsx` gọi `AuthProvider.register({ email, password })`.
4. `AuthProvider` thực hiện `register()`.
5. `AuthProvider` gọi `authApi.register(input)`.
6. `authApi` thực hiện `register()`.
7. `authApi` gọi `client.ts.api<T>()`.
8. `client.ts` thực hiện `api<T>()`, gửi request HTTP.
9. `client.ts` gọi `AuthController` qua `POST /api/auth/register`.
10. `AuthController` thực hiện `register()`.
11. `AuthController` gọi `AuthService.register(request)`.
12. `AuthService` thực hiện `register()`.
13. `AuthService` gọi `UserRepository.existsByEmailIgnoreCase(email)`.
14. `UserRepository` trả về kết quả `existsByEmailIgnoreCase`.
15. `AuthService` gọi hàm khởi tạo `User()` và các setter/builders.
16. `User` thực hiện hàm khởi tạo và gán các thuộc tính.
17. `AuthService` gọi `UserRepository.save(user)`.
18. `UserRepository` trả về `User` đã lưu.
19. `AuthService` trả `AuthResponse` cho `AuthController`.
20. `AuthController` trả `AuthResponse` cho `client.ts`.
21. `client.ts` trả `AuthResponse` cho `authApi`.
22. `authApi` trả `AuthResponse` cho `AuthProvider`.
23. `AuthProvider` trả `UserDto` cho `RegisterPage.tsx`.
24. `RegisterPage.tsx` hiển thị `ChooseRolePage`.
25. Người dùng chọn vai trò Ứng viên và xác nhận.
26. `ChooseRolePage.tsx` thực hiện `onSubmit()`.
27. `ChooseRolePage.tsx` gọi `AuthProvider.chooseRole(role)`.
28. `AuthProvider` thực hiện `chooseRole()`.
29. `AuthProvider` gọi `authApi.chooseRole(role)`.
30. `authApi` thực hiện `chooseRole()`.
31. `authApi` gọi `client.ts.api<T>()`.
32. `client.ts` thực hiện `api<T>()`, gửi request HTTP.
33. `client.ts` gọi `AuthController` qua `POST /api/auth/role`.
34. `AuthController` thực hiện `chooseRole()`.
35. `AuthController` gọi `AuthService.chooseRole(request)`.
36. `AuthService` thực hiện `chooseRole()`.
37. `AuthService` gọi `UserRepository.findById(userId)`.
38. `UserRepository` trả về `User`.
39. `AuthService` gọi `User.setRole()` và `User.setRoleChosen()`.
40. `User` thực hiện `setRole()` và `setRoleChosen()`.
41. `AuthService` gọi `UserRepository.save(user)`.
42. `UserRepository` trả về `User` đã cập nhật.
43. `AuthService` trả `AuthResponse` cho `AuthController`.
44. `AuthController` trả `AuthResponse` cho `client.ts`.
45. `client.ts` trả `AuthResponse` cho `authApi`.
46. `authApi` trả `AuthResponse` cho `AuthProvider`.
47. `AuthProvider` trả `UserDto` cho `ChooseRolePage.tsx`.
48. `ChooseRolePage.tsx` hiển thị và điều hướng tới trang chủ theo vai trò.

## Các bước suy ra biểu đồ

**Bước 1.** Dùng đúng các lifeline trang, lớp xử lý, repository và entity có trong `CLS-M1.json`; thứ tự trái sang phải theo actor → trang → client → controller → service/repository → entity. Phạm vi chuẩn là đăng ký mới rồi chọn vai trò Ứng viên.

**Bước 2.** Chuyển từng thao tác trong Kịch bản chuẩn V3 thành một message tuần tự, đánh số liên tục. Lời gọi qua các lớp dùng `call`; thao tác thực thi trên chính đối tượng dùng self-message; kết quả quay ngược dùng `return`; thao tác giao diện với actor dùng lời mô tả và `show`.

**Bước 3.** Đối chiếu tên API, handler, service, repository, entity và trang với mã nguồn. Luồng đăng ký gọi `existsByEmailIgnoreCase` rồi tạo và lưu `User`; luồng chọn vai trò lấy user bằng `findById`, cập nhật vai trò rồi lưu lại. `AuthService` đồng thời tạo token và `AuthResponse` trong xử lý nghiệp vụ; không thêm lifeline cho lớp không có trong `CLS-M1.json`.

Ta được biểu đồ tuần tự chức năng M1:

*Ghi chú: biểu đồ mô tả tuần tự đăng ký rồi chọn vai trò; đăng nhập tài khoản đã có là nhánh thay thế riêng trong kịch bản M1. Sau khi chọn vai trò, hồ sơ được provision ở lần gọi đầu tiên tới recruitment-service, không phải trong request chọn vai trò này.*

## Truy vết và điểm cần xác nhận

- Trang đăng ký và submit: `source/recruit_system/frontend/src/pages/RegisterPage.tsx:17-39`.
- Context và các lời gọi auth: `source/recruit_system/frontend/src/context/AuthContext.tsx:44-85`.
- API client: `source/recruit_system/frontend/src/api/client.ts:32-68`.
- Trang chọn vai trò: `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17-39`.
- Controller: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:12-34`.
- Service đăng ký/chọn vai trò: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28-66`.
- Repository: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/repository/UserRepository.java:8-10`.
- Entity: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/entity/User.java:17-55`.

`open_questions`: Không có.
