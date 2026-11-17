# M1-SEQ-FE — Ghi chú biểu đồ tuần tự chi tiết: Đăng nhập và chọn vai trò (Frontend)

- **ID:** M1-SEQ-FE · **Loại:** Sequence · **Package:** `07_TuanTu`
- **Tên diagram:** Biểu đồ tuần tự chi tiết - Đăng nhập và chọn vai trò (Frontend)
- **Kiến trúc:** Frontend React kết nối identity-service (Microservices, theo source).
- **Quy mô:** 7 lifelines (1 actor, 5 lớp FE từ M1-CLS-FE.json, 1 server controller), 25 messages, 2 combined fragment alt.

---

## 1. Kịch bản văn bản (khớp 1-1 với `seq`)

### Giai đoạn 1: Đăng nhập (LoginPage)
1. **seq 1 (`u` → `lp`):** Người dùng nhập email/mật khẩu và click Đăng nhập (`onSubmit()`).
2. **seq 2 (`lp` → `ap`):** `LoginPage` gọi `login(email, password)` từ `AuthProvider` (hook `useAuth`).
3. **seq 3 (`ap` → `api`):** `AuthProvider` gọi `authApi.login(email, password)`.
4. **seq 4 (`api` → `srv`):** `authApi` phát sinh HTTP request `POST /api/auth/login` kèm body `{ email, password }` sang `:AuthController` (identity-service).

#### Nhánh ngoại lệ: [sai email hoặc mật khẩu]
5. **seq 5 (`srv` → `api`):** Server trả về mã lỗi `401 Unauthorized`.
6. **seq 6 (`api` → `ap`):** Hàm `api()` ném ngoại lệ `ApiError(401, "Đăng nhập thất bại")`.
7. **seq 7 (`ap` → `lp`):** Lỗi lan truyền về `LoginPage.onSubmit()`.
8. **seq 8 (`lp` → `tp`):** `LoginPage` bắt lỗi trong khối `catch` và gọi `toast("Đăng nhập thất bại")` từ `ToastProvider` để hiển thị thông báo.

#### Nhánh thành công: [thông tin hợp lệ]
9. **seq 9 (`srv` → `api`):** Server trả về `200 OK` với body `{ token, user: { id, email, role, roleChosen: false } }`.
10. **seq 10 (`api` → `ap`):** `authApi` trả về đối tượng `AuthResponse`.
11. **seq 11 (`ap` → `lp`):** `AuthProvider` lưu token vào `localStorage`, cập nhật state `user` và trả về `UserDto`.
12. **seq 12 (`lp` → `tp`):** `LoginPage` gọi `toast("Đăng nhập thành công")`.
13. **seq 13 (`lp` → `crp`):** Do `user.roleChosen === false`, `accountPath(user)` trả về `"/choose-role"`. `LoginPage` thực hiện chuyển trang sang `:ChooseRolePage` (`navigate("/choose-role")`).

---

### Giai đoạn 2: Chọn vai trò lần đầu (ChooseRolePage)
14. **seq 14 (`u` → `crp`):** Người dùng chọn vai trò (ví dụ: `CANDIDATE`) và click Xác nhận vai trò (`onSubmit()`).
15. **seq 15 (`crp` → `ap`):** `ChooseRolePage` gọi `chooseRole("CANDIDATE")` từ `AuthProvider`.
16. **seq 16 (`ap` → `api`):** `AuthProvider` gọi `authApi.chooseRole("CANDIDATE")`.
17. **seq 17 (`api` → `srv`):** `authApi` gửi HTTP request `POST /api/auth/role` với header Bearer token sang `:AuthController`.

#### Nhánh ngoại lệ: [vai trò không hợp lệ hoặc đã chọn]
18. **seq 18 (`srv` → `api`):** Server trả về lỗi `400 Bad Request` hoặc `409 Conflict`.
19. **seq 19 (`api` → `ap`):** Ném `ApiError(status, message)`.
20. **seq 20 (`ap` → `crp`):** Lỗi lan truyền về `ChooseRolePage.onSubmit()`.
21. **seq 21 (`crp` → `tp`):** Khối `catch` gọi `toast(e.message)` hiển thị thông báo lỗi.

#### Nhánh thành công: [lưu vai trò thành công]
22. **seq 22 (`srv` → `api`):** Server trả về `200 OK` chứa token mới và `user` đã cập nhật (`role: "CANDIDATE"`, `roleChosen: true`).
23. **seq 23 (`api` → `ap`):** `authApi` trả về đối tượng `AuthResponse`.
24. **seq 24 (`ap` → `crp`):** `AuthProvider` cập nhật token mới và `user` mới vào Context, trả về `UserDto`.
25. **seq 25 (`crp` → `tp`):** `ChooseRolePage` gọi `toast("Đã lưu vai trò")`.

---

## 2. Bảng truy vết message → mã nguồn (file:dòng)

| Seq | Message | Từ | Đến | File nguồn & dòng code |
|---|---|---|---|---|
| 1 | `onSubmit()` | Người dùng | :LoginPage | `source/recruit_system/frontend/src/pages/LoginPage.tsx:29` |
| 2 | `login(email, password)` | :LoginPage | :AuthProvider | `source/recruit_system/frontend/src/pages/LoginPage.tsx:32` |
| 3 | `login(email, password)` | :AuthProvider | :authApi | `source/recruit_system/frontend/src/context/AuthContext.tsx:61-62` |
| 4 | `POST /api/auth/login` | :authApi | :AuthController | `source/recruit_system/frontend/src/api/client.ts:52-56` |
| 5 | return 401 error | :AuthController | :authApi | `source/recruit_system/frontend/src/api/client.ts:44-46` |
| 6 | return throw ApiError | :authApi | :AuthProvider | `source/recruit_system/frontend/src/api/client.ts:45` |
| 7 | return throw ApiError | :AuthProvider | :LoginPage | `source/recruit_system/frontend/src/pages/LoginPage.tsx:32-35` |
| 8 | `toast("Đăng nhập thất bại")` | :LoginPage | :ToastProvider | `source/recruit_system/frontend/src/pages/LoginPage.tsx:36` |
| 9 | return 200 { token, user } | :AuthController | :authApi | `source/recruit_system/frontend/src/api/client.ts:48` |
| 10 | return AuthResponse | :authApi | :AuthProvider | `source/recruit_system/frontend/src/context/AuthContext.tsx:62` |
| 11 | return UserDto | :AuthProvider | :LoginPage | `source/recruit_system/frontend/src/pages/LoginPage.tsx:32` |
| 12 | `toast("Đăng nhập thành công")` | :LoginPage | :ToastProvider | `source/recruit_system/frontend/src/pages/LoginPage.tsx:33` |
| 13 | `navigate("/choose-role")` | :LoginPage | :ChooseRolePage | `source/recruit_system/frontend/src/pages/LoginPage.tsx:34` |
| 14 | `onSubmit()` | Người dùng | :ChooseRolePage | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:28` |
| 15 | `chooseRole("CANDIDATE")` | :ChooseRolePage | :AuthProvider | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:31` |
| 16 | `chooseRole("CANDIDATE")` | :AuthProvider | :authApi | `source/recruit_system/frontend/src/context/AuthContext.tsx:75-76` |
| 17 | `POST /api/auth/role` | :authApi | :AuthController | `source/recruit_system/frontend/src/api/client.ts:63-67` |
| 18 | return 400/409 error | :AuthController | :authApi | `source/recruit_system/frontend/src/api/client.ts:44-46` |
| 19 | return throw ApiError | :authApi | :AuthProvider | `source/recruit_system/frontend/src/api/client.ts:45` |
| 20 | return throw ApiError | :AuthProvider | :ChooseRolePage | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:31-34` |
| 21 | `toast(e.message)` | :ChooseRolePage | :ToastProvider | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:35` |
| 22 | return 200 { token, user } | :AuthController | :authApi | `source/recruit_system/frontend/src/api/client.ts:48` |
| 23 | return AuthResponse | :authApi | :AuthProvider | `source/recruit_system/frontend/src/context/AuthContext.tsx:76` |
| 24 | return UserDto | :AuthProvider | :ChooseRolePage | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:31` |
| 25 | `toast("Đã lưu vai trò")` | :ChooseRolePage | :ToastProvider | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:32` |

---

## 3. Đối chiếu và ghi chú các điểm lệch so với biểu đồ hoạt động (`M1-ACT`)

1. **Phạm vi kịch bản:**
   - Trong `M1-ACT`, kịch bản mô tả cả 2 nhánh xuất phát điểm: Đăng ký (`RegisterPage`) và Đăng nhập (`LoginPage`), kết hợp luồng provisioning phía backend (`recruitment-service`).
   - Trong `M1-SEQ-FE`, do giới hạn số message (≤ 26 message) và tập trung vào biểu đồ tuần tự phía Frontend, kịch bản chọn luồng tương tác tiêu biểu: **Đăng nhập người dùng chưa chọn vai trò -> Đăng nhập thành công -> Điều hướng sang ChooseRolePage -> Chọn vai trò -> Cập nhật thành công**. Luồng đăng ký (`RegisterPage`) có cấu trúc gọi hàm và các bước tương tự (`onSubmit` -> `register` -> `authApi.register` -> `POST /api/auth/register`), chỉ khác endpoint và tên hàm.
2. **Khôi phục phiên và Profile Provisioning:**
   - `M1-ACT` có thể hiện luồng xác thực và provisioning tại `recruitment-service` (`ProfileProvisioningFilter` và `ProfileProvisioningService`). Tuy nhiên, ở tầng Frontend, các xử lý này diễn ra ngầm định ở server khi client gửi request tiếp theo. Biểu đồ FE dừng lại ở bước hoàn tất chọn vai trò và toast thành công.
3. **Tính nhất quán với `M1-CLS-FE.json`:**
   - Tất cả các lifelines object `:LoginPage`, `:ChooseRolePage`, `:AuthProvider`, `:ToastProvider`, `:authApi` đều nằm trong danh sách class của `M1-CLS-FE.json`.
   - Các operations (`onSubmit`, `login`, `chooseRole`, `toast`) khớp chính xác chữ ký phương thức đã định nghĩa trong `M1-CLS-FE.json`.
