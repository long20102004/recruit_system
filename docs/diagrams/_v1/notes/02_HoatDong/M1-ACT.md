# M1-ACT — Ghi chú biểu đồ hoạt động: Đăng ký, đăng nhập và chọn vai trò lần đầu

- **ID:** M1-ACT · **Loại:** Activity · **Package:** `02_HoatDong`
- **Tên diagram:** Biểu đồ hoạt động - Đăng ký, đăng nhập và chọn vai trò lần đầu (M1)
- **Kiến trúc:** Microservices (theo source, chốt 2026-11-17). Các làn: Người dùng, Frontend, identity-service, recruitment-service.
- **Giới hạn:** đúng 30 node (3 decision chính + 6 decision rẽ nhánh, không dùng fork/join vì code không có xử lý song song thực sự).

## Kịch bản

### Luồng chính 1 — Đăng ký lần đầu và chọn vai trò
1. Người dùng mở ứng dụng, chọn vào trang đăng ký (`n0` → `d0`).
2. `a1` — Nhập email và mật khẩu đăng ký trên `RegisterPage` (mật khẩu tối thiểu 6 ký tự).
3. `a2` — Frontend gửi `POST /api/auth/register` (qua nginx gateway tới identity-service:8081).
4. `d1` — identity-service kiểm tra dữ liệu hợp lệ (`@Valid`, `@Size(min=6)`) và email chưa tồn tại.
5. `a4` — Tạo `User` với `role=CANDIDATE`, `roleChosen=false`, mật khẩu mã hóa BCrypt.
6. `a5` — Sinh JWT bằng `JwtService.generateToken` (claim `email`, `role`).
7. `a6` — Frontend lưu token vào `localStorage` (`hirelens_token`) và `setUser`.
8. `a7` — Hiện toast "Tạo tài khoản thành công", điều hướng theo `accountPath`.
9. `d2` — `roleChosen=false` → `a8` hiển thị `ChooseRolePage`.
10. `c1` — Người dùng chọn vai trò CANDIDATE (Ứng viên) hoặc RECRUITER (Nhà tuyển dụng).
11. `c2` — Gửi `POST /api/auth/role` kèm Bearer token.
12. `d3` — identity-service kiểm tra role chỉ là CANDIDATE/RECRUITER và `roleChosen` còn `false`.
13. `c4` — Cập nhật `role`, `roleChosen=true` và lưu user.
14. `a5` — Sinh JWT mới chứa vai trò mới.
15. `a6` — Lưu token mới và cập nhật user trong `AuthContext`.
16. `a7` — Toast "Đã lưu vai trò", điều hướng `/candidate` hoặc `/recruiter`.
17. `a9` — Frontend tải trang chủ theo vai trò, gọi API kèm header `Authorization: Bearer`.
18. `f1` — recruitment-service xác thực JWT trong `JwtAuthenticationFilter`.
19. `d5` — Token hợp lệ → `p1` tra cứu user qua `GET /internal/users/{id}` của identity-service (SERVICE_TOKEN).
20. `d6` — Theo vai trò: `p2` tạo `candidate_profiles` nếu chưa có, hoặc `p3` tạo `company` + `recruiter_profiles` nếu chưa có.
21. `nF` — Trang chủ hiển thị dữ liệu; kết thúc.

### Luồng chính 2 — Đăng nhập khi đã có tài khoản, chưa chọn vai trò
1. `d0` [đã có tài khoản] → `b1` nhập email/mật khẩu trên `LoginPage`.
2. `b2` gửi `POST /api/auth/login`.
3. `d4` — Spring Security `authenticationManager.authenticate` kiểm tra; `d4` [đúng] → `a5` sinh JWT.
4. Tiếp bước 7–21 của Luồng chính 1 (`a6`, `a7`, `d2` [false], `a8`, `c1`…`nF`).

### Luồng chính 3 — Đăng nhập khi đã chọn vai trò
1. `b1`, `b2`, `d4` [đúng] → `a5` → `a6` → `a7`.
2. `d2` [roleChosen=true] → `a9` tải trang chủ theo vai trò (không qua ChooseRolePage).
3. `f1` → `d5` → `p1` → `d6` → `p2`/`p3` → `nF` (hồ sơ được tạo ở request đầu tiên tới recruitment-service).

### Luồng ngoại lệ E1 — Email đã tồn tại / dữ liệu đăng ký không hợp lệ
1. `d1` [email đã tồn tại (409) hoặc dữ liệu không hợp lệ (400)] → `a3` hiện lỗi ("Email đã được đăng ký" hoặc message từ `ApiError`).
2. `a3` → `a1`, người dùng nhập lại.

### Luồng ngoại lệ E2 — Sai thông tin đăng nhập
1. `d4` [sai email hoặc mật khẩu (401)] → `b3` hiện toast "Đăng nhập thất bại" / "Invalid email or password".
2. `b3` → `b1`, nhập lại.

### Luồng ngoại lệ E3 — Vai trò không hợp lệ hoặc đã chọn
1. `d3` [role không phải CANDIDATE/RECRUITER (400) hoặc roleChosen=true (409)] → `c3` hiện lỗi ("Chỉ được chọn ứng viên hoặc nhà tuyển dụng" / "Vai trò đã được lưu").
2. `c3` → `c1`, chọn lại.

### Luồng ngoại lệ E4 — Token không hợp lệ khi gọi recruitment-service
1. `d5` [token không hợp lệ] → `e1` trả lỗi 401 (JWT hết hạn/sai chữ ký, user không tìm thấy, tài khoản bị khóa).
2. `e1` → `nF` (frontend hiển thị lỗi từ `ApiError`).

## Luồng có thật trong code nhưng không vẽ (giới hạn 30 node)
- **Khôi phục phiên:** khi mở lại ứng dụng, `AuthProvider` đọc token trong `localStorage` và gọi `GET /api/auth/me`; token hỏng thì xóa (`setToken(null)`) — `frontend/src/context/AuthContext.tsx:48-59`.
- **Đăng xuất:** chỉ xóa token và user ở phía client, không gọi API — `AuthContext.tsx:82-85` (ngoài phạm vi module M1 như đã chốt).
- **Điều khiển truy cập route:** `RequireAuth` chặn route theo role và chuyển hướng `/choose-role` khi `roleChosen=false` — `frontend/src/App.tsx:22-37`.
- **Chỉ mục (index) định tuyến:** `HomeGate` điều hướng `/` tới trang chủ theo vai trò hoặc trang công khai — `App.tsx:39-44`.

## Bảng truy vết node → nguồn

| Node | Nguồn (file:dòng) | Ghi chú |
|---|---|---|
| `n0` | frontend/src/App.tsx:49-53 | Routes /login, /register, /choose-role |
| `d0` | frontend/src/pages/RegisterPage.tsx:77-78 | Link "Đã có tài khoản? Đăng nhập" (chiều ngược: LoginPage.tsx:77 "Chưa có tài khoản? Đăng ký") |
| `a1` | frontend/src/pages/RegisterPage.tsx:54-72 | Trường Email/Mật khẩu, minLength=6 |
| `a2` | frontend/src/api/client.ts:57-61 | `authApi.register` |
| `d1` | backend/identity-service/.../service/AuthService.java:29-31 | `existsByEmailIgnoreCase` → 409; `@Valid` ở AuthController.java:21-23 |
| `a3` | frontend/src/pages/RegisterPage.tsx:35-37 | Bắt `ApiError`, toast |
| `a4` | backend/identity-service/.../service/AuthService.java:33-42 | `User.builder()`, BCrypt qua `passwordEncoder` |
| `a5` | backend/common/.../security/JwtService.java:25-36 | `generateToken(userId, email, role)` |
| `a6` | frontend/src/context/AuthContext.tsx:68-72 | `setToken`, `setUser` |
| `a7` | frontend/src/pages/RegisterPage.tsx:33-34 | Toast + `navigate(accountPath)` |
| `d2` | frontend/src/utils/account.ts:3-4 | `roleChosen === false → "/choose-role"` |
| `a8` | frontend/src/pages/ChooseRolePage.tsx:41-52 | Trang chọn vai trò |
| `c1` | frontend/src/pages/ChooseRolePage.tsx:53-66 | `RoleOption` CANDIDATE / RECRUITER |
| `c2` | frontend/src/api/client.ts:63-67 | `authApi.chooseRole` |
| `d3` | backend/identity-service/.../service/AuthService.java:50-58 | Chỉ CANDIDATE/RECRUITER; `isRoleChosen()` → 409 |
| `c3` | frontend/src/pages/ChooseRolePage.tsx:34-36 | Toast lỗi |
| `c4` | backend/identity-service/.../service/AuthService.java:60-62 | `setRole`, `setRoleChosen(true)` |
| `b1` | frontend/src/pages/LoginPage.tsx:54-71 | Trường Email/Mật khẩu |
| `b2` | frontend/src/api/client.ts:52-56 | `authApi.login` |
| `d4` | backend/identity-service/.../service/AuthService.java:69-72 | `authenticationManager.authenticate`; 401 |
| `b3` | frontend/src/pages/LoginPage.tsx:35-37 | Toast "Đăng nhập thất bại" |
| `a9` | frontend/src/App.tsx:55-62 | Route `/candidate` (tương tự `/recruiter` App.tsx:96-103) |
| `f1` | backend/common/.../security/JwtAuthenticationFilter.java:28-51 | Đọc header Bearer, `isValid`, `principalLookup.load` |
| `d5` | backend/common/.../security/JwtAuthenticationFilter.java:35 | `jwtService.isValid(token)` |
| `e1` | backend/common/.../config/SecurityConfig.java:40 | `authenticationEntryPoint` trả 401 |
| `p1` | backend/common/.../security/RemotePrincipalLookup.java:17-25 | `GET {identity-url}/internal/users/{id}` |
| `d6` | backend/recruitment-service/.../service/ProfileProvisioningService.java:16-19 | Rẽ theo `user.getRole()` |
| `p2` | backend/recruitment-service/.../service/ProfileProvisioningService.java:16-17 | `candidates.insertIfAbsent(userId)` |
| `p3` | backend/recruitment-service/.../service/ProfileProvisioningService.java:18-25 | Tạo company rồi `recruiters.insertIfAbsent` |
| `nF` | frontend/src/utils/account.ts:5-6 | `/recruiter` hoặc `/candidate` |

Bổ sung (các cạnh quan trọng):
- `a2`/`b2`/`c2` → controller: `backend/identity-service/.../controller/AuthController.java:16-34` (`/api/auth/login|register|me|role`), route qua gateway `infra/gateway/nginx.conf:15-18`.
- `p1`: API nội bộ `backend/identity-service/.../controller/InternalUserController.java:15-16` (`GET /internal/users/{id}`), `/internal/*` bị nginx chặn từ ngoài (`infra/gateway/nginx.conf:14`).
- `f1` → `p1`/`d6`: `ProfileProvisioningFilter` chạy sau JWT filter (`SecurityConfig.java:53-54`) và gọi `ensureProfile` (`ProfileProvisioningFilter.java:19-21`).

## Mâu thuẫn và điểm cần lưu ý
1. **Báo cáo v6 (monolith) vs source (microservices):** đã chốt vẽ theo source (2026-11-17). File PDF báo cáo chưa có trên đĩa nên không đối chiếu được trang cụ thể cho M1; mọi truy vết ở trên đều dẫn về source.
2. **Tài liệu trong repo `docs/Module3_Interview_Flow.md`** chỉ mô tả luồng phỏng vấn (M4), không mô tả đăng ký/đăng nhập → không có mâu thuẫn văn bản nào cho M1 từ tài liệu repo.
3. **Không có mâu thuẫn code–code:** `ChooseRolePage.tsx:26` (`user.roleChosen !== false`) khớp `account.ts:4` và `AuthService.isRoleChosen()`; UI `minLength={6}` (RegisterPage.tsx:69) khớp `@Size(min=6)` (AuthDtos.java:22).
4. **Điểm mô hình hóa:** node `a5` "Sinh JWT" và `a6` "Lưu token" là node dùng chung cho cả 3 luồng (đăng ký, đăng nhập, chọn vai trò) để gọn hình; `c4` (chọn vai trò) tạo token mới chứa role mới rồi đi qua lại `a5`/`a6`.
5. **ADMIN:** chỉ tồn tại qua seed `V2__seed.sql:2`, không có luồng người dùng cấp ADMIN; `AuthService.chooseRole` từ chối role khác CANDIDATE/RECRUITER (AuthService.java:50-52).
