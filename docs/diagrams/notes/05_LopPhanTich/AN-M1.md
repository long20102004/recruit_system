# AN-M1 — Biểu đồ lớp pha phân tích chức năng đăng ký, đăng nhập và chọn vai trò

**Bước 1.** Từ các giao diện chính trong kịch bản ca sử dụng (KB-M1), đề xuất ba lớp biên tương ứng với các màn hình giao diện người dùng:

- `RegisterView`: Giao diện đăng ký tài khoản người dùng mới (`/register`).
  - Thuộc tính: `inEmail` (ô nhập email), `inPassword` (ô nhập mật khẩu ẩn, tối thiểu 6 ký tự), `outMessage` (thông báo kết quả tạo tài khoản hoặc lỗi), `subRegister` (nút "Tạo tài khoản"), `subToLogin` (liên kết "Đã có tài khoản? Đăng nhập"), `subBack` (liên kết "Quay lại danh sách việc làm").
  - Nguồn: `source/recruit_system/frontend/src/pages/RegisterPage.tsx:17-85`.
- `LoginView`: Giao diện đăng nhập tài khoản (`/login`).
  - Thuộc tính: `inEmail` (ô nhập email), `inPassword` (ô nhập mật khẩu ẩn), `outMessage` (thông báo kết quả đăng nhập hoặc lỗi), `subLogin` (nút "Đăng nhập"), `subToRegister` (liên kết "Chưa có tài khoản? Đăng ký"), `subBack` (liên kết "Quay lại danh sách việc làm").
  - Nguồn: `source/recruit_system/frontend/src/pages/LoginPage.tsx:17-84`.
- `ChooseRoleView`: Giao diện phân vai trò lần đầu cho tài khoản (`/choose-role`).
  - Thuộc tính: `inRole` (lựa chọn vai trò), `outsubRoleOptions` (danh sách hai thẻ lựa chọn có thể nhấp chọn: "Ứng viên" và "Nhà tuyển dụng"), `outMessage` (thông báo kết quả lưu vai trò hoặc lỗi), `subConfirmRole` (nút "Tiếp tục").
  - Nguồn: `source/recruit_system/frontend/src/pages/ChooseRolePage.tsx:17-73`.

Điều hướng giữa các lớp biên:
- Từ `RegisterView`, người dùng có thể chuyển sang `LoginView` qua liên kết `subToLogin` (`lnkLogin`, route `/login`); khi đăng ký thành công, hàm `accountPath` nhận diện `roleChosen === false` và điều hướng người dùng tới `ChooseRoleView` (`/choose-role`).
- Từ `LoginView`, người dùng có thể chuyển sang `RegisterView` qua liên kết `subToRegister` (`lnkRegister`, route `/register`); khi đăng nhập thành công tài khoản chưa phân vai trò (`roleChosen === false`), hệ thống điều hướng tới `ChooseRoleView` (`/choose-role`). Trường hợp tài khoản đã chọn vai trò trước đó (`roleChosen === true`), hệ thống chuyển hướng trực tiếp về trang chủ vai trò tương ứng (`/candidate` hoặc `/recruiter`).
- Từ `ChooseRoleView`, sau khi chọn vai trò và xác nhận thành công, hệ thống điều hướng tới trang chủ tương ứng (`/candidate` cho vai trò `CANDIDATE` hoặc `/recruiter` cho vai trò `RECRUITER`). Các trang chủ này thuộc phạm vi các module tiếp theo (M3 đối sánh và ứng tuyển), không bổ sung thêm lớp biên ngoài phạm vi M1.

**Bước 2.** Với các xử lý dữ liệu chính, sử dụng các hàm nghiệp vụ có thật trong mã nguồn backend (`AuthService` thuộc dịch vụ `identity-service`), phân công chúng cho lớp chủ thể `User` trong mô hình phân tích:

- Tên hàm: `register()`
  - Input: `request: AuthDtos.RegisterRequest` (chứa `email` và `password`).
  - Output: `AuthDtos.AuthResponse` (chứa chuỗi mã JWT và đối tượng thông tin người dùng `UserResponse`).
  - Lớp chủ thể: `User`.
  - Nguồn: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:28`.

- Tên hàm: `login()`
  - Input: `request: AuthDtos.LoginRequest` (chứa `email` và `password`).
  - Output: `AuthDtos.AuthResponse` (chứa chuỗi mã JWT và đối tượng thông tin người dùng `UserResponse`).
  - Lớp chủ thể: `User`.
  - Nguồn: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:68`.

- Tên hàm: `chooseRole()`
  - Input: `request: AuthDtos.ChooseRoleRequest` (chứa vai trò được chọn `role`: `CANDIDATE` hoặc `RECRUITER`).
  - Output: `AuthDtos.AuthResponse` (chứa chuỗi mã JWT mới mang vai trò cập nhật và `UserResponse` với `roleChosen = true`).
  - Lớp chủ thể: `User`.
  - Nguồn: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:49`.

- Tên hàm: `me()`
  - Input: Không có tham số tường minh (trích xuất danh tính `UserPrincipal` từ chuỗi JWT trong tiêu đề HTTP `Authorization`).
  - Output: `AuthDtos.UserResponse` (chứa `id`, `fullName`, `email`, `role`, `roleChosen`).
  - Lớp chủ thể: `User`.
  - Nguồn: `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:77`.

Các hàm trên trong kiến trúc triển khai thực tế thuộc `AuthService` của dịch vụ `identity-service`; việc phân công chúng vào lớp thực thể `User` là sự gán trách nhiệm nghiệp vụ trong pha phân tích hệ thống. `RegisterView` gọi hàm `register()`; `LoginView` gọi hàm `login()` và sử dụng `me()` để phục hồi phiên đăng nhập khi mở lại ứng dụng; `ChooseRoleView` gọi hàm `chooseRole()`. Lớp biên chỉ chứa các thuộc tính giao tiếp và điều hướng, không nắm giữ phương thức nghiệp vụ.

Giữ các lớp thực thể liên quan từ biểu đồ trích thực thể TT gồm `User` (thuộc dịch vụ `identity-service`), `CandidateProfile`, `RecruiterProfile` và `Company` (thuộc dịch vụ `recruitment-service`), cùng toàn bộ các thuộc tính nghiệp vụ không kiểu và các mối quan hệ:
- `CandidateProfile` (1) – `User` (1): Liên kết logic giữa hai microservice qua trường `userId`, thể hiện một người dùng có thể sở hữu tối đa một hồ sơ ứng viên (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/CandidateProfile.java:26`).
- `RecruiterProfile` (n) – `User` (1): Liên kết logic giữa hai microservice qua trường `userId`, thể hiện một người dùng nhà tuyển dụng có thể gắn với hồ sơ đại diện tại công ty (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/RecruiterProfile.java:23`).
- `RecruiterProfile` (n) – `Company` (1): Quan hệ liên kết trong `recruitment-service`, mỗi hồ sơ nhà tuyển dụng thuộc về một công ty xác định (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/entity/RecruiterProfile.java:27`).

Hậu điều kiện của chức năng M1 là tự động khởi tạo hồ sơ tương ứng tại `recruitment-service` khi người dùng truy cập sau khi hoàn tất chọn vai trò: `CandidateProfile` cho ứng viên, hoặc `Company` và `RecruiterProfile` cho nhà tuyển dụng (thực thi ngầm qua `ProfileProvisioningFilter` và `ProfileProvisioningService.ensureProfile()`, nguồn `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/service/ProfileProvisioningService.java:15`).

Ta được biểu đồ lớp pha phân tích chức năng đăng ký, đăng nhập và chọn vai trò:

### open_questions

- [cần xác nhận] Sau khi chọn vai trò hoặc đăng nhập thành công, điều hướng sang `/candidate` hoặc `/recruiter` dẫn tới các chức năng tiếp theo (M3 đối sánh/ứng tuyển); các lớp biên của trang chủ vai trò không được đưa vào M1 nhằm bảo đảm đúng phạm vi chức năng.
- [cần xác nhận] Cơ chế tạo hồ sơ tự động qua `ProfileProvisioningService` trong `recruitment-service` là xử lý ngầm định của bộ lọc khi có request đầu tiên đến `recruitment-service`, không được gọi trực tiếp từ giao diện `ChooseRolePage`.
