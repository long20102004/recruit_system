# Thiết kế biểu đồ lớp chi tiết chức năng đăng ký, đăng nhập và chọn vai trò

Frontend sử dụng React 19, Vite và TypeScript; backend sử dụng Spring Boot 4.1 và Spring Data JPA. Các dịch vụ AI trong hệ thống dùng FastAPI, nhưng không có lời gọi AI trong chức năng M1. Các component, context, object và module TypeScript được biểu diễn bằng hộp lớp để mô tả thiết kế, không hàm ý chúng là lớp được khai báo trong source.

## Bước 1. Xác định các lớp giao diện

### a. Tầng giao diện

Tên `txt…`, `btn…` dưới đây là tên mô hình hóa đề xuất cho các phần tử JSX, không phải biến được khai báo trong mã. Các state và dữ liệu context là thuộc tính ẩn.

- **RegisterPage.tsx** (`frontend/src/pages/RegisterPage.tsx:17`): thuộc tính tường minh gồm `txtEmail: input`, `txtPassword: input`, `btnRegister: Button`, `btnLogin: link`, `btnBack: link`; thuộc tính ẩn gồm `email: string`, `password: string`, `busy: boolean`, `user: UserDto | null`, `loading: boolean`. Trang gọi backend gián tiếp qua `useAuth().register`, `AuthProvider` và `authApi.register`. Đăng ký thành công chuyển theo `accountPath`: tài khoản chưa chọn vai trò tới `/choose-role`; nếu đã chọn thì tới `/candidate` hoặc `/recruiter`. Liên kết đăng nhập tới `/login`, quay lại tới `/`.
- **LoginPage.tsx** (`frontend/src/pages/LoginPage.tsx:17`): thuộc tính tường minh gồm `txtEmail: input`, `txtPassword: input`, `btnLogin: Button`, `btnRegister: link`, `btnBack: link`; thuộc tính ẩn gồm `email: string`, `password: string`, `busy: boolean`, `user: UserDto | null`, `loading: boolean`. Trang gọi backend gián tiếp qua `useAuth().login`, `AuthProvider` và `authApi.login`. Đăng nhập thành công chuyển theo `accountPath`; liên kết đăng ký tới `/register`, quay lại tới `/`.
- **ChooseRolePage.tsx** (`frontend/src/pages/ChooseRolePage.tsx:17`): thuộc tính tường minh gồm `btnCandidate: RoleOption`, `btnRecruiter: RoleOption`, `btnConfirmRole: Button`; thuộc tính ẩn gồm `role: Exclude<RoleDto, "ADMIN">`, `busy: boolean`, `user: UserDto | null`, `loading: boolean`. Hai lựa chọn cập nhật state, nút tiếp tục gọi backend gián tiếp qua `useAuth().chooseRole`. Thành công chuyển tới `/candidate` hoặc `/recruiter`; nếu chưa đăng nhập trang chuyển tới `/login`; nếu đã chọn vai trò thì chuyển theo `accountPath`.

`AuthProvider` quản lý `user`, `loading`, token và các hàm xác thực; khi khởi tạo có token, provider gọi `authApi.me()` để khôi phục người dùng. Các trang dùng toast để thông báo thành công hoặc lỗi. Các route đích `/candidate`, `/recruiter` và `/` thuộc phạm vi giao diện khác nên không đưa thêm lớp vào hình.

Quan hệ giữa các giao diện: `RegisterPage.tsx` ⇄ `LoginPage.tsx`; sau xác thực có thể chuyển tới `ChooseRolePage.tsx`; chọn vai trò xong chuyển tới trang chủ theo vai trò. Hướng chuyển chính xác phụ thuộc `accountPath` (`frontend/src/utils/account.ts:3`). Ảnh chụp giao diện và hình ghép điều hướng cần bổ sung khi dựng báo cáo.

## Bước 2. Xác định lớp thao tác cơ sở dữ liệu

### b. Tầng thao tác CSDL

Spring Data JPA cung cấp vai trò DAO thông qua repository; không tạo lớp `DAO` hay `EntityManager` giả. Các hàm sau lấy theo chữ ký source; các hàm `save` và `findById` được kế thừa từ `JpaRepository`.

- **AuthService** (`identity-service/.../service/AuthService.java:20`):
  - `register(request: AuthDtos.RegisterRequest): AuthDtos.AuthResponse` — Input: email, mật khẩu; Output: token và người dùng; kiểm tra email, mã hóa mật khẩu, lưu `User`.
  - `login(request: AuthDtos.LoginRequest): AuthDtos.AuthResponse` — Input: email, mật khẩu; Output: token và người dùng sau xác thực.
  - `chooseRole(request: AuthDtos.ChooseRoleRequest): AuthDtos.AuthResponse` — Input: vai trò; Output: token và người dùng đã cập nhật.
  - `me(): AuthDtos.UserResponse` — Input: principal từ security context, không có tham số; Output: thông tin người dùng.
- **UserRepository** (`identity-service/.../repository/UserRepository.java:8`): `findByEmailIgnoreCase(email: String): Optional<User>` — Input: email; Output: người dùng nếu có. `existsByEmailIgnoreCase(email: String): boolean` — Input: email; Output: kết quả tồn tại. Ngoài ra `save` lưu người dùng và `findById` tìm theo ID qua API kế thừa.
- **ProfileProvisioningService** (`recruitment-service/.../service/ProfileProvisioningService.java:10`): `ensureProfile(user: UserPrincipal): void` — Input: principal đã xác thực; Output: không trả dữ liệu, bảo đảm hồ sơ ứng viên hoặc nhà tuyển dụng tương ứng. Nhánh nhà tuyển dụng tạo hoặc tìm công ty rồi tạo hồ sơ.
- **CandidateProfileRepository** (`recruitment-service/.../repository/CandidateProfileRepository.java:8`): `insertIfAbsent(userId: Integer): void` — Input: ID người dùng; Output: không trả dữ liệu; thêm hồ sơ ứng viên nếu chưa có.
- **RecruiterProfileRepository** (`recruitment-service/.../repository/RecruiterProfileRepository.java:11`): `findFirstByUserIdOrderByCreatedAtAsc(userId: Integer): Optional<RecruiterProfile>` — Input: ID người dùng; Output: hồ sơ đầu tiên nếu có. `insertIfAbsent(userId: Integer, companyId: Integer): void` — Input: ID người dùng và công ty; Output: không trả dữ liệu.
- **CompanyRepository** (`recruitment-service/.../repository/CompanyRepository.java:8`): `insertIfAbsent(name: String): void` — Input: tên công ty; Output: không trả dữ liệu. `findByNameIgnoreCase(name: String): Optional<Company>` — Input: tên công ty; Output: công ty nếu có.

`ProfileProvisioningFilter` gọi `ensureProfile` khi request tới recruitment-service có `UserPrincipal`; việc chọn vai trò tại identity-service không trực tiếp gọi service này. Do đó không vẽ mũi tên đồng bộ từ `AuthService` sang `ProfileProvisioningService`.

## Bước 3. Xác định lớp thực thể

### c. Tầng thực thể

`User` thuộc identity-service; `CandidateProfile`, `RecruiterProfile`, `Company` thuộc recruitment-service. Giữ quan hệ E1: hai profile tham chiếu logic tới `User` qua `userId`, không có khóa ngoại xuyên service; `Company` kết tập các `RecruiterProfile` qua thuộc tính `company` thật. Thuộc tính `listRecruiterProfile` là đề xuất trong E1, không có trong entity Java. Kiểu ngày và số trong hình dùng kiểu Java thật (`LocalDateTime`, `LocalDate`, `BigDecimal`), thay cho ký hiệu khái quát E1 (`DateTime`, `Date`, `Decimal`); `User.roleChosen` là `boolean`.

## Bước 4. Xác định lớp phụ trợ và mối quan hệ

### d. Lớp phụ trợ

- Module `frontend/src/api/client.ts` đảm nhiệm vai trò HTTPClient: `api<T>(path: string, options: RequestInit = {}): Promise<T>` dùng `fetch`, gắn bearer token khi có và xử lý lỗi; object `authApi` cung cấp `login`, `register`, `me`, `chooseRole`.
- `AuthController` là REST controller tại `/api/auth`: nhận lần lượt `POST /login`, `POST /register`, `GET /me`, `POST /role` và ủy quyền cho `AuthService`. Trên hình, các nhãn HTTP là đường dẫn đầy đủ qua gateway. Việc `GET /me` chủ yếu phục vụ khôi phục phiên của `AuthProvider`.
- `ProfileProvisioningFilter` là filter của recruitment-service, không phải controller; nó chuyển principal sang `ProfileProvisioningService`. M1 không có client gọi AI hay route FastAPI, nên không đưa lớp AI vào hình.

**Phân tích mẫu thiết kế:** Repository tách truy cập JPA khỏi nghiệp vụ và cho phép Spring Data cung cấp các truy vấn theo tên; DTO (`AuthDtos` và các kiểu frontend) tách dữ liệu trao đổi khỏi entity, giảm lộ chi tiết lưu trữ; dependency injection qua constructor và `@RequiredArgsConstructor` giúp controller/service nhận phụ thuộc rõ ràng, thuận tiện thay thế khi kiểm thử. API Gateway nginx định tuyến `/api/auth` tới identity-service; module `client.ts` tập trung cơ chế HTTP và token, giúp các trang không lặp lại logic gọi mạng. Đây là gateway định tuyến và module bao gọi HTTP thực tế, không giả định có một lớp Gateway/Adapter riêng trong M1.

Ta được biểu đồ lớp chi tiết chức năng đăng ký, đăng nhập và chọn vai trò:
