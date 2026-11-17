# Thiết kế biểu đồ hoạt động chức năng đăng ký, đăng nhập và chọn vai trò

Chức năng M1 "Đăng ký, đăng nhập và chọn vai trò" thuộc Hệ thống tuyển dụng thông minh HireLens cho phép người dùng khởi tạo tài khoản mới bằng email và mật khẩu, xác thực danh tính vào hệ thống và thiết lập vai trò nghiệp vụ ban đầu (Ứng viên hoặc Nhà tuyển dụng). Biểu đồ hoạt động được thiết kế tuân thủ nghiêm ngặt quy tắc mẫu báo cáo PTIT (mục 10 của skill `ptit-uml-diagrams`) và thống nhất hoàn toàn với biểu đồ lớp chi tiết CLS-M1.

---

## Bước 1. Xác định các phân vùng (làn / partition) của biểu đồ hoạt động

Dựa trên biểu đồ lớp chi tiết CLS-M1 và cấu trúc mã nguồn thực tế của hệ thống HireLens, các làn hoạt động được phân chia theo từng trang giao diện và từng tầng kiến trúc như sau:

1. **Lớp giao diện `RegisterPage.tsx`** (`source/recruit_system/frontend/src/pages/RegisterPage.tsx:17`):
   - Đảm nhiệm giao diện đăng ký tài khoản mới tại route `/register`.
   - Thuộc tính mô hình hóa: `txtEmail`, `txtPassword`, `btnRegister`, `btnLogin`, `btnBack`.
   - Chứa luồng nhập thông tin tài khoản, xử lý gửi form đăng ký, nhận kết quả và chuyển hướng.

2. **Lớp giao diện `LoginPage.tsx`** (`source/recruit_system/frontend/src/pages/LoginPage.tsx:17`):
   - Đảm nhiệm giao diện đăng nhập hệ thống tại route `/login`.
   - Thuộc tính mô hình hóa: `txtEmail`, `txtPassword`, `btnLogin`, `btnRegister`, `btnBack`.
   - Chứa luồng nhập thông tin đăng nhập, xử lý xác thực, kiểm tra cờ vai trò `roleChosen` và điều hướng tương ứng.

3. **Lớp giao diện `ChooseRolePage.tsx`** (`source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17`):
   - Đảm nhiệm giao diện chọn vai trò lần đầu tại route `/choose-role`.
   - Thuộc tính mô hình hóa: `btnCandidate`, `btnRecruiter`, `btnConfirmRole`.
   - Tiếp nhận người dùng vừa đăng ký thành công hoặc đăng nhập với tài khoản chưa chọn vai trò (`roleChosen = false`), cho phép chọn vai trò `CANDIDATE` hoặc `RECRUITER` và lưu cấu hình một lần duy nhất.

4. **Làn `client` (vai trò HTTPClient)** (`source/recruit_system/frontend/src/api/client.ts:32`):
   - Đại diện cho module mạng phía frontend (`client.ts`), đóng vai trò như lớp `HTTPClient` trong mẫu PTIT.
   - Chứa hàm gọi HTTP `api<T>()` thực hiện thao tác `fetch()`, gắn chuỗi Bearer token vào tiêu đề `Authorization`, chuyển đổi tham số JSON và xử lý lỗi mạng `ApiError`.

5. **Làn `AuthController` (vai trò RestController)** (`source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:12`):
   - Đại diện cho tầng RestController trong Spring Boot tại dịch vụ `identity-service` (cổng 8081).
   - Đảm nhiệm vai trò `requestMapping()` điều hướng các yêu cầu HTTP từ Gateway: `register()` (`POST /api/auth/register`), `login()` (`POST /api/auth/login`), `chooseRole()` (`POST /api/auth/role`), đồng thời kích hoạt kiểm tra tính hợp lệ dữ liệu `@Valid`.

6. **Làn `AuthService` (vai trò Service/Repository)** (`source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:20`):
   - Đại diện cho tầng nghiệp vụ và truy xuất cơ sở dữ liệu (tương ứng vai trò Service/DAO trong mẫu thiết kế).
   - Trực tiếp tương tác với `UserRepository` (Spring Data JPA) để thao tác bảng `users`, mã hóa mật khẩu BCrypt qua `PasswordEncoder`, kiểm tra nghiệp vụ và sinh mã xác thực JWT qua `JwtService`.

---

## Bước 2. Liệt kê các hành động (action) chuẩn hóa theo từng làn

Các hành động trên biểu đồ được chuẩn hóa theo đúng các khuôn mẫu của môn học: *"Hiện giao diện"*, *"Lấy từ form: …"*, *"Lưu vào state/session: …"*, *"Gọi hàm f()"*, *"Thông báo …"*. Mỗi thao tác gửi yêu cầu từ giao diện nối hai chiều qua chuỗi: Trang giao diện → `client` (`fetch()`) → `AuthController` (`<handler>()`) → `AuthService` (`Gọi hàm f()`) rồi quay ngược lại trang giao diện để kiểm tra kết quả qua Decision `[Thành công]` / `[Thất bại]`.

### 1. Phân vùng `RegisterPage.tsx`
- `n_start` (Initial node): "Bắt đầu" chu trình người dùng tương tác hệ thống.
- `act_reg_show`: "Hiện giao diện" đăng ký với biểu mẫu nhập email và mật khẩu.
- `dec_has_account`: Decision "Đã có tài khoản?" rẽ nhánh theo lựa chọn của người dùng:
  - `[Chưa có tài khoản]`: Người dùng nhập thông tin đăng ký mới.
  - `[Đã có tài khoản]`: Nhấp liên kết "Đăng nhập", chuyển sang giao diện `LoginPage.tsx`.
- `act_reg_form`: "Lấy từ form: email, password" khi người dùng nhấn nút "Tạo tài khoản".
- `act_reg_call`: "Gọi hàm register()" kích hoạt hàm `register` từ `AuthContext` / `authApi`.
- `dec_reg_result`: Decision "Kết quả đăng ký" đánh giá phản hồi từ máy chủ:
  - `[Thất bại]`: Chuyển sang `act_reg_err` "Thông báo lỗi đăng ký" (email trùng lặp HTTP 409 hoặc dữ liệu sai định dạng HTTP 400), người dùng nhấp `[Click OK]` để quay lại form sửa đổi.
  - `[Thành công]`: Chuyển sang `act_reg_save` "Lưu vào state/session: token, user" (ghi nhớ token vào `localStorage` và cập nhật state `user`).
- `act_reg_toast`: "Thông báo tạo tài khoản thành công" và điều hướng sang trang chọn vai trò `ChooseRolePage.tsx`.

### 2. Phân vùng `LoginPage.tsx`
- `act_login_show`: "Hiện giao diện" đăng nhập với biểu mẫu nhập email và mật khẩu.
- `act_login_form`: "Lấy từ form: email, password" khi người dùng nhấn nút "Đăng nhập".
- `act_login_call`: "Gọi hàm login()" kích hoạt hàm `login` từ `AuthContext` / `authApi`.
- `dec_login_result`: Decision "Kết quả đăng nhập" tiếp nhận phản hồi từ backend:
  - `[Thất bại]`: Chuyển sang `act_login_err` "Thông báo sai thông tin đăng nhập" (sai mật khẩu hoặc email chưa đăng ký HTTP 401), `[Click OK]` quay lại form để nhập lại.
  - `[Thành công]`: Chuyển sang `act_login_save` "Lưu vào state/session: token, user".
- `act_login_toast`: "Thông báo đăng nhập thành công".
- `dec_role_chosen`: Decision "Đã chọn vai trò?" đánh giá cờ `user.roleChosen`:
  - `[Chưa chọn vai trò]` (`roleChosen = false`): Điều hướng sang `ChooseRolePage.tsx` để hoàn tất cấu hình.
  - `[Đã chọn vai trò]` (`roleChosen = true`): Điều hướng về trang chủ chuyên biệt (`/candidate` hoặc `/recruiter`), dẫn tới điểm kết thúc `n_final`.

### 3. Phân vùng `ChooseRolePage.tsx`
- `merge_choose_role`: Điểm gộp (Merge node) tiếp nhận luồng từ đăng ký mới hoặc từ đăng nhập khi tài khoản chưa chọn vai trò.
- `act_role_show`: "Hiện giao diện" chọn vai trò với hai thẻ lựa chọn `Ứng viên` và `Nhà tuyển dụng`.
- `act_role_form`: "Lấy từ form: role" khi người dùng chọn một vai trò và bấm "Tiếp tục".
- `act_role_call`: "Gọi hàm chooseRole()" gửi dữ liệu vai trò được chọn.
- `dec_role_result`: Decision "Kết quả chọn vai trò":
  - `[Thất bại]`: Chuyển sang `act_role_err` "Thông báo lỗi chọn vai trò" (HTTP 400 hoặc 409), `[Click OK]` quay lại form chọn lại.
  - `[Thành công]`: Chuyển sang `act_role_save` "Lưu vào state/session: token mới, user" (lưu JWT mới chứa vai trò cập nhật).
- `act_role_toast`: "Thông báo lưu vai trò thành công".
- `merge_final`: Điểm gộp dẫn tới node kết thúc.
- `n_final` (Activity Final node): "Kết thúc" toàn bộ chu trình xác thực và phân quyền của chức năng M1.

### 4. Phân vùng `client` (HTTPClient)
- `act_client_reg`: "fetch()" đóng gói dữ liệu và gửi yêu cầu `POST /api/auth/register`.
- `act_client_login`: "fetch()" đóng gói dữ liệu và gửi yêu cầu `POST /api/auth/login`.
- `act_client_role`: "fetch()" gắn tiêu đề Bearer token và gửi yêu cầu `POST /api/auth/role`.

### 5. Phân vùng `AuthController` (RestController)
- `act_ctrl_reg`: "register()" tiếp nhận `AuthDtos.RegisterRequest`, kích hoạt xác thực `@Valid` và chuyển tiếp sang `AuthService`.
- `act_ctrl_login`: "login()" tiếp nhận `AuthDtos.LoginRequest`, xác thực dữ liệu và chuyển tiếp sang `AuthService`.
- `act_ctrl_role`: "chooseRole()" tiếp nhận `AuthDtos.ChooseRoleRequest` và chuyển tiếp sang `AuthService`.

### 6. Phân vùng `AuthService` (Service/Repository)
- `act_svc_reg`: "Gọi hàm register()" kiểm tra email chưa tồn tại (`userRepository.existsByEmailIgnoreCase`), băm mật khẩu bằng BCrypt, lưu bản ghi `User` mới (`role = CANDIDATE`, `roleChosen = false`) vào CSDL `hirelens_identity`, sinh chuỗi JWT và trả về `AuthResponse`.
- `act_svc_login`: "Gọi hàm login()" thực hiện xác thực qua `AuthenticationManager.authenticate()`, truy vấn tài khoản qua `userRepository.findByEmailIgnoreCase()`, sinh JWT và trả về `AuthResponse`.
- `act_svc_role`: "Gọi hàm chooseRole()" xác nhận vai trò hợp lệ, kiểm tra `isRoleChosen() == false`, cập nhật `role` và `roleChosen = true`, lưu vào CSDL, sinh JWT mới chứa vai trò chính thức và trả về `AuthResponse`.

Ta được biểu đồ hoạt động chức năng đăng ký, đăng nhập và chọn vai trò:

---

## 3. Bảng truy vết chi tiết phần tử biểu đồ → Mã nguồn dự án (`src`)

Bảng dưới đây đối chiếu tất cả 36 node (gồm 1 Initial, 1 Final, 27 Action, 5 Decision, 2 Merge) và 40 Flow trên biểu đồ hoạt động ACT-M1 với các dòng mã nguồn thực tế trong thư mục `source/recruit_system/`:

| STT | Khóa phần tử (`key`) | Làn (Partition) | Loại node / Luồng | Tên hiển thị / Nhãn Guard | Nguồn truy vết mã nguồn (`src`) |
| :---: | :---| :---| :---| :---| :---|
| 1 | `RegisterPage` | — | Partition | `RegisterPage.tsx` | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:17` |
| 2 | `LoginPage` | — | Partition | `LoginPage.tsx` | `source/recruit_system/frontend/src/pages/LoginPage.tsx:17` |
| 3 | `ChooseRolePage` | — | Partition | `ChooseRolePage.tsx` | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17` |
| 4 | `client` | — | Partition | `client` | `source/recruit_system/frontend/src/api/client.ts:32` |
| 5 | `AuthController` | — | Partition | `AuthController` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:12` |
| 6 | `AuthService` | — | Partition | `AuthService` | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:20` |
| 7 | `n_start` | `RegisterPage` | initial | Bắt đầu | `source/recruit_system/frontend/src/App.tsx:52` |
| 8 | `act_reg_show` | `RegisterPage` | action | Hiện giao diện | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:43` |
| 9 | `dec_has_account` | `RegisterPage` | decision | Đã có tài khoản? | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:77-78` |
| 10 | `act_reg_form` | `RegisterPage` | action | Lấy từ form: email, password | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:54-72` |
| 11 | `act_reg_call` | `RegisterPage` | action | Gọi hàm register() | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:29-32` |
| 12 | `act_client_reg` | `client` | action | fetch() | `source/recruit_system/frontend/src/api/client.ts:43` |
| 13 | `act_ctrl_reg` | `AuthController` | action | register() | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:21-24` |
| 14 | `act_svc_reg` | `AuthService` | action | Gọi hàm register() | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28-46` |
| 15 | `dec_reg_result` | `RegisterPage` | decision | Kết quả đăng ký | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:32-36` |
| 16 | `act_reg_err` | `RegisterPage` | action | Thông báo lỗi đăng ký | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:35-37` |
| 17 | `act_reg_save` | `RegisterPage` | action | Lưu vào state/session: token, user | `source/recruit_system/frontend/src/context/AuthContext.tsx:68-73` |
| 18 | `act_reg_toast` | `RegisterPage` | action | Thông báo tạo tài khoản thành công | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:33` |
| 19 | `act_login_show` | `LoginPage` | action | Hiện giao diện | `source/recruit_system/frontend/src/pages/LoginPage.tsx:43` |
| 20 | `act_login_form` | `LoginPage` | action | Lấy từ form: email, password | `source/recruit_system/frontend/src/pages/LoginPage.tsx:54-71` |
| 21 | `act_login_call` | `LoginPage` | action | Gọi hàm login() | `source/recruit_system/frontend/src/pages/LoginPage.tsx:29-32` |
| 22 | `act_client_login` | `client` | action | fetch() | `source/recruit_system/frontend/src/api/client.ts:43` |
| 23 | `act_ctrl_login` | `AuthController` | action | login() | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:16-19` |
| 24 | `act_svc_login` | `AuthService` | action | Gọi hàm login() | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:68-75` |
| 25 | `dec_login_result` | `LoginPage` | decision | Kết quả đăng nhập | `source/recruit_system/frontend/src/pages/LoginPage.tsx:32-36` |
| 26 | `act_login_err` | `LoginPage` | action | Thông báo sai thông tin đăng nhập | `source/recruit_system/frontend/src/pages/LoginPage.tsx:35-37` |
| 27 | `act_login_save` | `LoginPage` | action | Lưu vào state/session: token, user | `source/recruit_system/frontend/src/context/AuthContext.tsx:61-66` |
| 28 | `act_login_toast` | `LoginPage` | action | Thông báo đăng nhập thành công | `source/recruit_system/frontend/src/pages/LoginPage.tsx:33` |
| 29 | `dec_role_chosen` | `LoginPage` | decision | Đã chọn vai trò? | `source/recruit_system/frontend/src/utils/account.ts:3-6` |
| 30 | `merge_choose_role` | `ChooseRolePage` | merge | *(Merge chọn vai trò)* | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17` |
| 31 | `act_role_show` | `ChooseRolePage` | action | Hiện giao diện | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:42-52` |
| 32 | `act_role_form` | `ChooseRolePage` | action | Lấy từ form: role | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:53-66` |
| 33 | `act_role_call` | `ChooseRolePage` | action | Gọi hàm chooseRole() | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:28-31` |
| 34 | `act_client_role` | `client` | action | fetch() | `source/recruit_system/frontend/src/api/client.ts:43` |
| 35 | `act_ctrl_role` | `AuthController` | action | chooseRole() | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:31-34` |
| 36 | `act_svc_role` | `AuthService` | action | Gọi hàm chooseRole() | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:48-66` |
| 37 | `dec_role_result` | `ChooseRolePage` | decision | Kết quả chọn vai trò | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:31-35` |
| 38 | `act_role_err` | `ChooseRolePage` | action | Thông báo lỗi chọn vai trò | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:34-36` |
| 39 | `act_role_save` | `ChooseRolePage` | action | Lưu vào state/session: token mới, user | `source/recruit_system/frontend/src/context/AuthContext.tsx:75-80` |
| 40 | `act_role_toast` | `ChooseRolePage` | action | Thông báo lưu vai trò thành công | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:32` |
| 41 | `merge_final` | `ChooseRolePage` | merge | *(Merge kết thúc)* | `source/recruit_system/frontend/src/utils/account.ts:5-6` |
| 42 | `n_final` | `ChooseRolePage` | final | Kết thúc | `source/recruit_system/frontend/src/utils/account.ts:5-6` |

---

## 4. Đối chiếu kịch bản nghiệp vụ và đặc tả kịch bản (KB-M1)

Biểu đồ hoạt động ACT-M1 bao quát đầy đủ 3 luồng hoạt động chính và các nhánh ngoại lệ thực tế được mô tả trong tài liệu kịch bản chuẩn và ngoại lệ `diagrams/notes/02_KichBan/KB-M1.md`:

1. **Luồng chuẩn 1 — Đăng ký tài khoản mới và chọn vai trò lần đầu:**
   - Người dùng bắt đầu tại `RegisterPage.tsx`, nhập email và mật khẩu hợp lệ (`demo1234`).
   - Lời gọi đi qua `client.ts` (`fetch()`) tới `AuthController.register()` và `AuthService.register()`.
   - CSDL tạo `User` mới với `role = CANDIDATE`, `roleChosen = false`, cấp mã JWT.
   - Frontend lưu token, hiển thị thông báo thành công và chuyển sang `ChooseRolePage.tsx`.
   - Người dùng chọn vai trò (ví dụ `CANDIDATE` hoặc `RECRUITER`), gọi `authApi.chooseRole()`.
   - `AuthService.chooseRole()` cập nhật `roleChosen = true`, cấp JWT mới.
   - Kết thúc chu trình đăng ký và phân quyền.

2. **Luồng chuẩn 2 — Đăng nhập với tài khoản chưa chọn vai trò:**
   - Tại `RegisterPage.tsx`, người dùng chọn liên kết "Đăng nhập", chuyển sang `LoginPage.tsx`.
   - Nhập thông tin đăng nhập tài khoản hợp lệ, gọi `authApi.login()`.
   - `AuthService.login()` xác thực thành công và trả về thông tin người dùng với `roleChosen = false`.
   - Decision `dec_role_chosen` nhận diện `roleChosen = false`, điều hướng người dùng tới `ChooseRolePage.tsx` qua `merge_choose_role` để thực hiện tiếp các bước chọn vai trò tương tự Luồng 1.

3. **Luồng chuẩn 3 — Đăng nhập với tài khoản đã chọn vai trò trước đó:**
   - Người dùng nhập thông tin đăng nhập tài khoản có sẵn (`candidate@hirelens.local` hoặc `recruiter@hirelens.local`).
   - Xác thực thành công tại `identity-service`, `AuthService.login()` trả về `roleChosen = true`.
   - Decision `dec_role_chosen` nhận diện `roleChosen = true`, lập tức chuyển thẳng tới `merge_final` và kết thúc luồng xác thực M1 mà không cần đi qua bước chọn vai trò.

4. **Các luồng ngoại lệ và xử lý lỗi:**
   - *Ngoại lệ đăng ký:* Trùng email đã đăng ký (HTTP 409 Conflict) hoặc vi phạm kiểm tra `@Valid` (HTTP 400 Bad Request) → Decision `dec_reg_result` rẽ nhánh `[Thất bại]`, hiển thị thông báo lỗi tại `act_reg_err` và quay lại form đăng ký sau khi người dùng nhấp OK.
   - *Ngoại lệ đăng nhập:* Sai email hoặc mật khẩu (HTTP 401 Unauthorized) → Decision `dec_login_result` rẽ nhánh `[Thất bại]`, hiển thị thông báo sai thông tin tại `act_login_err` và quay lại form đăng nhập.
   - *Ngoại lệ chọn vai trò:* Vai trò gửi lên không hợp lệ hoặc tài khoản đã hoàn tất chọn vai trò trước đó (HTTP 400/409) → Decision `dec_role_result` rẽ nhánh `[Thất bại]`, hiển thị lỗi tại `act_role_err` và cho phép người dùng thao tác lại.

5. **Tính gọn gàng và tuân thủ giới hạn:**
   - Toàn bộ biểu đồ có đúng **36 node** (thỏa mãn yêu cầu `<= 40 node`).
   - Các luồng phụ trợ như khôi phục phiên tự động bằng `authApi.me()` khi mở lại ứng dụng hoặc đăng xuất phía client không đưa vào biểu đồ chính để tránh làm rối cấu trúc theo đúng phân tích trong `KB-M1.md` và `CLS-M1.md`.
