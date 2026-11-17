# UC-M1 — Ghi chú biểu đồ Use case chi tiết: Đăng ký, đăng nhập, chọn vai trò

- **ID:** UC-M1 · **Loại:** Use case · **Package:** `01_UseCase`
- **Tên diagram:** Biểu đồ Use Case chi tiết - Đăng ký, đăng nhập, chọn vai trò (M1)
- **Kiến trúc:** Microservices (identity-service quản lý tài khoản và JWT, recruitment-service tự động khởi tạo hồ sơ người dùng).
- **Phạm vi:** Toàn bộ chức năng đăng ký, xác thực đăng nhập, lưu phiên JWT, lựa chọn vai trò lần đầu (`roleChosen=false`) và điều hướng tới giao diện trang chủ theo vai trò tương ứng.

---

## Các bước suy diễn biểu đồ (theo mẫu báo cáo PTIT)

### Bước 1: Xác định use case chính và các actor liên quan
Sao chép use case và các actor liên quan từ biểu đồ Use case tổng quan (UC0):
- **Use case chính:** `Đăng ký, đăng nhập, chọn vai trò` (`UC_M1`) – đây là chức năng gốc thuộc Module 1 của hệ thống HireLens.
- **Actor trực tiếp (tổng quát):** `Người dùng` (`UserActor`) – đại diện cho bất kỳ người dùng nào truy cập vào hệ thống HireLens qua trình duyệt web.
- **Actor chuyên biệt (con):**
  - `Ứng viên` (`CandidateActor`): Người dùng mang vai trò `CANDIDATE`, có mục tiêu tìm việc, nộp CV và tham gia phỏng vấn.
  - `Nhà tuyển dụng` (`RecruiterActor`): Người dùng mang vai trò `RECRUITER`, có mục tiêu đăng tin tuyển dụng, quản lý hồ sơ ứng viên và câu hỏi phỏng vấn.
- Hai actor con nối tới actor cha `Người dùng` bằng quan hệ kế thừa (**Generalization**).

### Bước 2: Xác định các use case chi tiết từ các giao diện chính
Mỗi giao diện chính (trang/hộp thoại thật trong frontend của chức năng M1) tương ứng với 1 use case chi tiết:
1. Giao diện Đăng nhập (`LoginPage.tsx`, route `/login`) → Use case chi tiết **Đăng nhập** (`UC_Login`).
2. Giao diện Đăng ký (`RegisterPage.tsx`, route `/register`) → Use case chi tiết **Đăng ký tài khoản** (`UC_Register`).
3. Giao diện Chọn vai trò (`ChooseRolePage.tsx`, route `/choose-role`) → Use case chi tiết **Chọn vai trò** (`UC_ChooseRole`).
4. Giao diện Trang chủ Ứng viên (`CandidateHomePage.tsx`, route `/candidate`) → Use case chi tiết **Xem trang chủ ứng viên** (`UC_CandidateHome`).
5. Giao diện Trang chủ Nhà tuyển dụng (`RecruiterHomePage.tsx`, route `/recruiter`) → Use case chi tiết **Xem trang chủ nhà tuyển dụng** (`UC_RecruiterHome`).

### Bước 3: Xét quan hệ với use case chính
Phân loại quan hệ dựa trên tính chất nghiệp vụ và luồng điều hướng:
1. **Quan hệ `<<include>>` (Bước bắt buộc):**
   - Use case chính `Đăng ký, đăng nhập, chọn vai trò` bao gồm bước bắt buộc là **Đăng nhập** (`UC_Login`). Người dùng cần xác thực danh tính để hệ thống cấp JWT token và nhận diện phiên làm việc trước khi thực hiện các tác vụ của từng vai trò.
2. **Quan hệ `<<extend>>` (Bước tùy chọn kèm Extension Points trên use case gốc):**
   - Use case gốc `Đăng ký, đăng nhập, chọn vai trò` khai báo 4 extension points:
     - `Chưa có tài khoản`: Mở rộng bởi use case **Đăng ký tài khoản** (`UC_Register`). Bước này chỉ diễn ra khi người dùng chưa có tài khoản trong hệ thống và chọn chuyển sang trang đăng ký.
     - `Chưa chọn vai trò`: Mở rộng bởi use case **Chọn vai trò** (`UC_ChooseRole`). Bước này chỉ diễn ra khi tài khoản vừa được đăng ký mới hoặc chưa từng thiết lập vai trò (`roleChosen = false`).
     - `Vai trò Ứng viên`: Mở rộng bởi use case **Xem trang chủ ứng viên** (`UC_CandidateHome`). Bước này diễn ra sau khi xác thực thành công và người dùng mang vai trò `CANDIDATE`.
     - `Vai trò Nhà tuyển dụng`: Mở rộng bởi use case **Xem trang chủ nhà tuyển dụng** (`UC_RecruiterHome`). Bước này diễn ra sau khi xác thực thành công và người dùng mang vai trò `RECRUITER`.
3. **Quan hệ `Association` (Giao tiếp với Actor):**
   - Actor `Người dùng` liên kết trực tiếp với use case chính `Đăng ký, đăng nhập, chọn vai trò`.
   - Actor `Ứng viên` liên kết trực tiếp với use case `Xem trang chủ ứng viên`.
   - Actor `Nhà tuyển dụng` liên kết trực tiếp với use case `Xem trang chủ nhà tuyển dụng`.

### Bước 4: Mô tả chi tiết từng use case

#### 1. Use case chính: Đăng ký, đăng nhập, chọn vai trò (`UC_M1`)
- **Tác nhân:** Người dùng (chính), Ứng viên, Nhà tuyển dụng.
- **Mục tiêu:** Cung cấp cổng xác thực và quản lý truy cập vào hệ thống HireLens, giúp người dùng đăng ký tài khoản, đăng nhập an toàn bằng JWT và định tuyến đúng không gian làm việc theo vai trò.
- **Tiền điều kiện:** Người dùng có thiết bị kết nối mạng và trình duyệt truy cập hệ thống HireLens.
- **Hậu điều kiện:** Người dùng được xác thực danh tính, phiên đăng nhập được lưu trữ (JWT token lưu trong `localStorage`), hồ sơ vai trò tương ứng được khởi tạo và giao diện chính theo vai trò được hiển thị.

#### 2. Use case chi tiết: Đăng nhập (`UC_Login`)
- **Tác nhân:** Người dùng.
- **Giao diện tương ứng:** `LoginPage.tsx` (route `/login`).
- **Mục tiêu:** Xác thực tài khoản qua email và mật khẩu.
- **Luồng sự kiện:** Người dùng nhập email và mật khẩu, nhấn nút "Đăng nhập". Hệ thống gửi `POST /api/auth/login` tới `identity-service`. Khi thông tin chính xác, hệ thống trả về mã JWT Bearer token và thông tin người dùng (`UserResponse`). Token được lưu vào `localStorage`, cập nhật `AuthContext`.
- **Ngoại lệ:** Sai email hoặc mật khẩu, hệ thống trả lỗi HTTP 401, hiển thị thông báo "Đăng nhập thất bại" và giữ lại giao diện đăng nhập.

#### 3. Use case chi tiết: Đăng ký tài khoản (`UC_Register`)
- **Tác nhân:** Người dùng.
- **Giao diện tương ứng:** `RegisterPage.tsx` (route `/register`).
- **Mục tiêu:** Tạo tài khoản mới trong hệ thống HireLens.
- **Luồng sự kiện:** Người dùng nhập email và mật khẩu (tối thiểu 6 ký tự), nhấn "Tạo tài khoản". Hệ thống gửi `POST /api/auth/register` tới `identity-service`. Backend tạo bản ghi `User` mới với `role = CANDIDATE`, `roleChosen = false`, mã hóa mật khẩu bằng BCrypt, trả về JWT token và thông tin người dùng. Trình duyệt lưu token và chuyển hướng sang `/choose-role`.
- **Ngoại lệ:** Email đã tồn tại (HTTP 409) hoặc mật khẩu dưới 6 ký tự (HTTP 400), hiển thị lỗi và yêu cầu nhập lại.

#### 4. Use case chi tiết: Chọn vai trò (`UC_ChooseRole`)
- **Tác nhân:** Người dùng.
- **Giao diện tương ứng:** `ChooseRolePage.tsx` (route `/choose-role`).
- **Mục tiêu:** Cho phép người dùng mới thiết lập vai trò làm việc một lần duy nhất.
- **Luồng sự kiện:** Người dùng chọn thẻ "Ứng viên" (`CANDIDATE`) hoặc "Nhà tuyển dụng" (`RECRUITER`), nhấn "Tiếp tục". Frontend gửi `POST /api/auth/role` kèm Bearer token. `identity-service` cập nhật `role` và gán `roleChosen = true`, tái tạo JWT token mới phản ánh vai trò mới.
- **Ngoại lệ:** Vai trò không hợp lệ hoặc tài khoản đã từng chọn vai trò trước đó (HTTP 409), hiển thị thông báo lỗi.

#### 5. Use case chi tiết: Xem trang chủ ứng viên (`UC_CandidateHome`)
- **Tác nhân:** Ứng viên (`CandidateActor`).
- **Giao diện tương ứng:** `CandidateHomePage.tsx` (route `/candidate`).
- **Mục tiêu:** Hiển thị không gian làm việc tìm việc, xem danh sách việc làm phù hợp và quản lý đơn ứng tuyển.
- **Luồng sự kiện:** Sau khi xác thực với vai trò `CANDIDATE`, route `/candidate` được tải. Request đầu tiên mang Bearer token đi qua `ProfileProvisioningFilter` tại `recruitment-service`, tự động gọi `ProfileProvisioningService.ensureProfile` để chèn bản ghi vào bảng `candidate_profiles` nếu chưa có, sau đó hiển thị dữ liệu trang chủ ứng viên.

#### 6. Use case chi tiết: Xem trang chủ nhà tuyển dụng (`UC_RecruiterHome`)
- **Tác nhân:** Nhà tuyển dụng (`RecruiterActor`).
- **Giao diện tương ứng:** `RecruiterHomePage.tsx` (route `/recruiter`).
- **Mục tiêu:** Hiển thị không gian làm việc quản trị tin tuyển dụng, hồ sơ ứng tuyển và thống kê tuyển dụng.
- **Luồng sự kiện:** Sau khi xác thực với vai trò `RECRUITER`, route `/recruiter` được tải. Request đầu tiên mang Bearer token đi qua `ProfileProvisioningFilter` tại `recruitment-service`, tự động khởi tạo bản ghi công ty (`companies`) và hồ sơ nhà tuyển dụng (`recruiter_profiles`) nếu chưa có, sau đó trả về số liệu tổng quan trên trang chủ nhà tuyển dụng.

---

Ta được biểu đồ Use case chi tiết chức năng M1 "Đăng ký, đăng nhập, chọn vai trò":

*(Hình ảnh biểu đồ được dựng và xuất từ spec `diagrams/specs/01_UseCase/UC-M1.json` bằng công cụ Visual Paradigm)*

---

## Bảng truy vết phần tử và quan hệ về mã nguồn

| STT | Phần tử / Quan hệ | Loại | Mô tả / Tên gọi | Nguồn mã nguồn (file:dòng) |
|:---:|---|---|---|---|
| 1 | `UserActor` | Actor | Người dùng (trình duyệt web) | `source/recruit_system/frontend/src/App.tsx:22-37` |
| 2 | `CandidateActor` | Actor | Ứng viên (role CANDIDATE) | `source/recruit_system/backend/common/src/main/java/recruit/demo/entity/Role.java:4` |
| 3 | `RecruiterActor` | Actor | Nhà tuyển dụng (role RECRUITER) | `source/recruit_system/backend/common/src/main/java/recruit/demo/entity/Role.java:5` |
| 4 | `SystemBoundary` | System | Hệ thống HireLens - Phân hệ Xác thực và Quản lý tài khoản (Module 1) | `source/recruit_system/frontend/src/App.tsx:46-54` |
| 5 | `UC_M1` | Use Case | Đăng ký, đăng nhập, chọn vai trò | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:16-34` |
| 6 | `UC_Login` | Use Case | Đăng nhập | `source/recruit_system/frontend/src/pages/LoginPage.tsx:17-85` |
| 7 | `UC_Register` | Use Case | Đăng ký tài khoản | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:17-86` |
| 8 | `UC_ChooseRole` | Use Case | Chọn vai trò | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17-74` |
| 9 | `UC_CandidateHome` | Use Case | Xem trang chủ ứng viên | `source/recruit_system/frontend/src/pages/candidate/CandidateHomePage.tsx:36-258` |
| 10 | `UC_RecruiterHome` | Use Case | Xem trang chủ nhà tuyển dụng | `source/recruit_system/frontend/src/pages/recruiter/RecruiterHomePage.tsx:28-138` |
| 11 | `CandidateActor` → `UserActor` | Generalization | Kế thừa tác nhân Người dùng | `source/recruit_system/backend/common/src/main/java/recruit/demo/entity/Role.java:4` |
| 12 | `RecruiterActor` → `UserActor` | Generalization | Kế thừa tác nhân Người dùng | `source/recruit_system/backend/common/src/main/java/recruit/demo/entity/Role.java:5` |
| 13 | `UserActor` → `UC_M1` | Association | Tác nhân tương tác use case chính | `source/recruit_system/frontend/src/App.tsx:49-53` |
| 14 | `CandidateActor` → `UC_CandidateHome` | Association | Tương tác trang chủ ứng viên | `source/recruit_system/frontend/src/App.tsx:55-62` |
| 15 | `RecruiterActor` → `UC_RecruiterHome` | Association | Tương tác trang chủ nhà tuyển dụng | `source/recruit_system/frontend/src/App.tsx:97-103` |
| 16 | `UC_M1` → `UC_Login` | Include | Bao gồm bước xác thực bắt buộc | `source/recruit_system/frontend/src/pages/LoginPage.tsx:29-35` |
| 17 | `UC_Register` → `UC_M1` | Extend | Mở rộng tại điểm "Chưa có tài khoản" | `source/recruit_system/frontend/src/pages/RegisterPage.tsx:29-35` |
| 18 | `UC_ChooseRole` → `UC_M1` | Extend | Mở rộng tại điểm "Chưa chọn vai trò" | `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:28-34` |
| 19 | `UC_CandidateHome` → `UC_M1` | Extend | Mở rộng tại điểm "Vai trò Ứng viên" | `source/recruit_system/frontend/src/utils/account.ts:6` |
| 20 | `UC_RecruiterHome` → `UC_M1` | Extend | Mở rộng tại điểm "Vai trò Nhà tuyển dụng" | `source/recruit_system/frontend/src/utils/account.ts:5` |

---

## Ghi chú kỹ thuật và điểm đối chiếu

1. **Kiến trúc Microservices và Profile Provisioning:**
   - Trong quá trình đăng ký hoặc đăng nhập tại `identity-service`, người dùng chỉ được tạo bản ghi trong bảng `users` (`hirelens_identity`).
   - Việc tạo hồ sơ cụ thể (`candidate_profiles` hoặc `company` + `recruiter_profiles`) thuộc CSDL `hirelens_recruitment` diễn ra tự động thông qua `ProfileProvisioningFilter` và `ProfileProvisioningService.ensureProfile` khi người dùng truy cập trang chủ lần đầu. Đây là xử lý ngầm (background logic) ở tầng backend, không tách thành giao diện người dùng riêng.
2. **Vai trò ADMIN:**
   - Trong source code, vai trò `ADMIN` chỉ tồn tại qua dữ liệu khởi tạo sẵn (seed migration `V2__seed.sql`).
   - `AuthService.chooseRole` (dòng 50-52) chặn nghiêm ngặt: chỉ cho phép chọn `CANDIDATE` hoặc `RECRUITER`. Do đó, hệ thống không có luồng giao diện nào cho phép người dùng tự đăng ký hoặc tự chọn quyền ADMIN. Theo quyết định thiết kế đã thống nhất (2026-11-17), không vẽ use case riêng cho ADMIN.
3. **Quản lý phiên làm việc:**
   - Đăng nhập và đăng ký đều trả về JWT Bearer token và đối tượng `UserResponse`. Frontend lưu token vào `localStorage` (`hirelens_token`) và duy trì trạng thái đăng nhập qua `AuthContext`.
