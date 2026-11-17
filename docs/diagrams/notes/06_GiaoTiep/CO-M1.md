# CO-M1 — Biểu đồ giao tiếp pha phân tích chức năng đăng ký, đăng nhập và chọn vai trò

**Bước 1. Xây dựng kịch bản chuẩn V2 cho luồng chính:**

Căn cứ vào kịch bản ca sử dụng chuẩn (Happy Path) trong `KB-M1.md` và các lớp, phương thức nghiệp vụ đã được xác định trong biểu đồ lớp pha phân tích `AN-M1.json`, ta xây dựng kịch bản chuẩn V2 đánh số liên tục cho luồng chính. Mỗi bước được diễn đạt bằng đúng một câu chuẩn hóa theo quy chuẩn phân tích:

1. Người dùng nhập email, mật khẩu và click đăng ký.
2. RegisterView gọi User để xử lý.
3. User thực hiện hàm register().
4. User trả kết quả cho RegisterView.
5. RegisterView gọi ChooseRoleView để xử lý.
6. ChooseRoleView hiển thị cho Người dùng.
7. Người dùng chọn vai trò ứng viên và click tiếp tục.
8. ChooseRoleView gọi User để xử lý.
9. User thực hiện hàm chooseRole().
10. User trả kết quả cho ChooseRoleView.
11. ChooseRoleView hiển thị cho Người dùng.

**Bước 2. Xác định các đối tượng tham gia và đường liên kết (Link):**

Từ các lớp xuất hiện trong kịch bản chuẩn V2 (được trích từ biểu đồ lớp pha phân tích `AN-M1.json`), ta xác định tác nhân và các đối tượng giao tiếp:
- **Tác nhân (Actor):** `Người dùng` (`UserActor`) — người dùng thao tác trực tiếp trên trình duyệt web.
- **Đối tượng lớp biên (Boundary):**
  - `:RegisterView` (lớp `RegisterView`, stereotype `boundary`) — giao diện đăng ký tài khoản mới (`/register`).
  - `:ChooseRoleView` (lớp `ChooseRoleView`, stereotype `boundary`) — giao diện chọn vai trò lần đầu cho tài khoản (`/choose-role`).
- **Đối tượng lớp thực thể (Entity):**
  - `:User` (lớp `User`, stereotype `entity`) — thực thể tài khoản người dùng, đồng thời là lớp chủ thể tiếp nhận trách nhiệm thực thi các hàm nghiệp vụ xác thực trong pha phân tích.

Xác định 6 đường liên kết (Link) giữa các cặp đối tượng có tương tác trao đổi thông điệp:
- Liên kết giữa `Người dùng` và `:RegisterView`: truyền nhận thông tin đăng ký tài khoản mới.
- Liên kết giữa `:RegisterView` và `:User`: gửi yêu cầu đăng ký và nhận kết quả xác thực ban đầu (kèm token JWT).
- Liên kết tự thân (Self-link) trên `:User`: thực hiện các hàm xử lý nội tại của lớp chủ thể `User` (`register()` và `chooseRole()`).
- Liên kết giữa `:RegisterView` và `:ChooseRoleView`: điều hướng giao diện người dùng sau khi đăng ký thành công (`navigate("/choose-role")`).
- Liên kết giữa `:ChooseRoleView` và `Người dùng`: hiển thị giao diện chọn vai trò, nhận lựa chọn vai trò từ người dùng và phản hồi kết quả hoàn tất.
- Liên kết giữa `:ChooseRoleView` và `:User`: gửi yêu cầu cập nhật vai trò được chọn và nhận mã JWT cập nhật.

**Bước 3. Gán các thông điệp (Message) đánh số liên tục khớp 1-1 với kịch bản chuẩn V2:**

Các thông điệp được đánh số thứ tự liên tục từ 1 đến 11, với nhãn ngắn gọn quy chuẩn (`register`, `call`, `return`, `show`, `chooseRole`, cùng tên hàm kèm ngoặc tròn cho bước tự thực hiện hàm trên self-link):
- `1: register` (từ `Người dùng` tới `:RegisterView`): Người dùng gửi biểu mẫu đăng ký gồm email và mật khẩu qua nút "Tạo tài khoản".
- `2: call` (từ `:RegisterView` tới `:User`): Lớp biên gọi hàm nghiệp vụ đăng ký trên lớp chủ thể `User`.
- `3: register()` (tự gửi trên `:User`): Đối tượng thực thể `User` tự thực hiện logic băm mật khẩu, tạo bản ghi người dùng và cấp mã JWT.
- `4: return` (từ `:User` tới `:RegisterView`): Trả kết quả đăng ký thành công cùng mã token về cho lớp biên.
- `5: call` (từ `:RegisterView` tới `:ChooseRoleView`): Lớp biên kích hoạt điều hướng sang màn hình chọn vai trò lần đầu.
- `6: show` (từ `:ChooseRoleView` tới `Người dùng`): Màn hình chọn vai trò kết xuất các thẻ tùy chọn vai trò ("Ứng viên" / "Nhà tuyển dụng") hiển thị cho người dùng.
- `7: chooseRole` (từ `Người dùng` tới `:ChooseRoleView`): Người dùng nhấp chọn thẻ "Ứng viên" và nhấn nút "Tiếp tục".
- `8: call` (từ `:ChooseRoleView` tới `:User`): Lớp biên gọi hàm cập nhật vai trò trên lớp chủ thể `User`.
- `9: chooseRole()` (tự gửi trên `:User`): Đối tượng `User` tự thực hiện kiểm tra vai trò hợp lệ, ghi nhận `role = CANDIDATE`, `roleChosen = true` và cấp mã JWT mới.
- `10: return` (từ `:User` tới `:ChooseRoleView`): Trả kết quả cập nhật thành công kèm mã token mới về cho lớp biên.
- `11: show` (từ `:ChooseRoleView` tới `Người dùng`): Lớp biên hiển thị thông báo lưu thành công và sẵn sàng chuyển tiếp sang trang chủ vai trò.

Ta được biểu đồ giao tiếp pha phân tích chức năng đăng ký, đăng nhập và chọn vai trò:

---

## Bảng truy vết phần tử và thông điệp → mã nguồn (`src`)

| Loại | Ký hiệu / Tên | Vai trò / Mô tả | Nguồn truy vết (`src`) |
| :--- | :--- | :--- | :--- |
| **Actor** | `Người dùng` (`UserActor`) | Tác nhân người dùng thao tác qua trình duyệt | `source/recruit_system/frontend/src/App.tsx:22` |
| **Object** | `:RegisterView` | Đối tượng lớp biên đăng ký tài khoản (boundary) | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:17` |
| **Object** | `:ChooseRoleView` | Đối tượng lớp biên chọn vai trò ban đầu (boundary) | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17` |
| **Object** | `:User` | Đối tượng thực thể người dùng, lớp chủ thể nghiệp vụ (entity) | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/entity/User.java:17` |
| **Link** | `UserActor` – `RegisterView` | Đường tương tác người dùng trên giao diện đăng ký | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:42` |
| **Link** | `RegisterView` – `User` | Đường gọi xử lý đăng ký tài khoản tới backend | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:32` |
| **Link** | `User` – `User` (Self-link) | Đường tự xử lý logic nội tại của thực thể User | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28` |
| **Link** | `RegisterView` – `ChooseRoleView` | Đường điều hướng giao diện giữa hai lớp biên | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:34` |
| **Link** | `ChooseRoleView` – `UserActor` | Đường hiển thị và tiếp nhận tương tác chọn vai trò | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:41` |
| **Link** | `ChooseRoleView` – `User` | Đường gọi xử lý lưu vai trò tới backend | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:31` |
| **Message 1** | `1: register` | `UserActor` → `RegisterView`: Nhập form và submit | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:74` |
| **Message 2** | `2: call` | `RegisterView` → `User`: Gọi hàm đăng ký | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:32` |
| **Message 3** | `3: register()` | `User` → `User`: Xử lý tạo User và cấp JWT | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28` |
| **Message 4** | `4: return` | `User` → `RegisterView`: Trả kết quả `AuthResponse` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:45` |
| **Message 5** | `5: call` | `RegisterView` → `ChooseRoleView`: Điều hướng `/choose-role` | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:34` |
| **Message 6** | `6: show` | `ChooseRoleView` → `UserActor`: Hiển thị form chọn vai trò | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:41` |
| **Message 7** | `7: chooseRole` | `UserActor` → `ChooseRoleView`: Chọn vai trò và bấm "Tiếp tục" | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:67` |
| **Message 8** | `8: call` | `ChooseRoleView` → `User`: Gọi hàm lưu vai trò | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:31` |
| **Message 9** | `9: chooseRole()` | `User` → `User`: Cập nhật `role` và cấp JWT mới | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:49` |
| **Message 10** | `10: return` | `User` → `ChooseRoleView`: Trả kết quả cập nhật thành công | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:65` |
| **Message 11** | `11: show` | `ChooseRoleView` → `UserActor`: Thông báo toast "Đã lưu vai trò" | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:33` |

---

## Ghi chú và câu hỏi mở

### Ghi chú thiết kế:
- Toàn bộ các lớp và hàm tham gia trong biểu đồ (`RegisterView`, `ChooseRoleView`, `User`, cùng các phương thức `register()`, `chooseRole()`) đều tuân thủ nguyên tắc kế thừa trực tiếp từ biểu đồ lớp pha phân tích `AN-M1.json`.
- Kịch bản chuẩn V2 phản ánh đúng chu trình tuần tự của luồng chính (Happy Path): tạo tài khoản người dùng mới và chọn vai trò khởi đầu, phù hợp với tiến trình nghiệp vụ thực tế của dự án HireLens.

### Câu hỏi mở (Open Questions):
- `[cần xác nhận]` Biểu đồ giao tiếp pha phân tích CO-M1 tập trung đặc tả luồng chính (Happy Path) gồm đăng ký tài khoản mới và phân định vai trò lần đầu; luồng đăng nhập tài khoản có sẵn qua `LoginView` (sử dụng hàm `login()` và `me()`) được quản lý như kịch bản ngoại lệ/thay thế đã trình bày chi tiết trong `KB-M1.md` và `ST-M1`.
- `[cần xác nhận]` Quá trình tự động tạo `CandidateProfile` hoặc `RecruiterProfile` trong `recruitment-service` được thực hiện ngầm định tại tầng hạ tầng (`ProfileProvisioningFilter`) khi người dùng truy cập trang chủ vai trò lần đầu, không phát sinh thông điệp trực tiếp từ lớp biên `ChooseRoleView` trong pha phân tích M1.
