# M1-CLS-BE — Lớp chi tiết Backend

## Vai trò và luồng gọi

- `AuthController` nhận các endpoint `/api/auth/login`, `/register`, `/me`, `/role` và chuyển xử lý sang `AuthService`.
- `AuthService` kiểm tra/đăng nhập tài khoản, lưu `User` qua `UserRepository`, và yêu cầu `JwtService` phát token. DTO trong `AuthDtos` là request/response của API.
- `UserRepository` là Spring Data JPA repository cho `User`.
- Khi request đã xác thực tới recruitment-service, `ProfileProvisioningFilter` lấy `UserPrincipal` từ security context và gọi `ProfileProvisioningService.ensureProfile`. Service phân nhánh theo role, tạo candidate profile hoặc company/recruiter profile qua các repository.
- `JwtService` tạo và xác minh token JWT dùng chung; `UserPrincipal` là đối tượng principal/security user.

## Pattern có thật trong code

1. **Repository** — `UserRepository extends JpaRepository<User, Integer>` (`source/recruit_system/backend/identity-service/src/main/java/recruit/demo/repository/UserRepository.java:167-170`); các `CandidateProfileRepository`, `RecruiterProfileRepository`, `CompanyRepository` cũng là Spring Data repository (`source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CandidateProfileRepository.java:691-697`, `RecruiterProfileRepository.java:722-739`, `CompanyRepository.java:705-711`). Tách truy cập dữ liệu khỏi nghiệp vụ đăng nhập và provisioning; giúp HireLens tái sử dụng thao tác truy vấn/lưu và hỗ trợ tạo hồ sơ idempotent (`insertIfAbsent`).
2. **DTO (Data Transfer Object)** — các record request/response trong `AuthDtos` (`source/recruit_system/backend/common/src/main/java/recruit/demo/dto/AuthDtos.java:479-509`). API chỉ trao đổi email/mật khẩu, role, token và dữ liệu user cần trả; không trả entity `User` trực tiếp, giảm lộ dữ liệu như `passwordHash`.
3. **Dependency Injection** — các dependency được inject qua constructor do Lombok `@RequiredArgsConstructor`, ví dụ `AuthController.authService` và `AuthService.userRepository/jwtService` (`source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:11-14`, `service/AuthService.java:83-90`). Cho phép ghép các service/repository theo Spring container, tránh tự khởi tạo phụ thuộc trong từng request.
4. **Strategy qua interface và cấu hình lựa chọn triển khai** — `PrincipalLookup` định nghĩa `load`, `RemotePrincipalLookup implements PrincipalLookup` dùng HTTP đến identity-service (`source/recruit_system/backend/common/src/main/java/recruit/demo/security/PrincipalLookup.java:373-376`, `RemotePrincipalLookup.java:385-403`); `JwtAuthenticationFilter` phụ thuộc interface (`JwtAuthenticationFilter.java:333-339`). Source còn có `CustomUserDetailsService implements PrincipalLookup` cho triển khai cục bộ (`source/recruit_system/backend/identity-service/src/main/java/recruit/demo/security/CustomUserDetailsService.java:237-253`). Cách trừu tượng này cho phép dùng xác thực JWT thống nhất trong nhiều service, trong khi nguồn tra cứu principal phù hợp với cấu hình service.

## Bảng truy vết chính

| Nhóm | Nguồn |
|---|---|
| REST controller và chữ ký endpoint | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/controller/AuthController.java:12-34` |
| Luồng nghiệp vụ đăng ký/đăng nhập/chọn role | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/service/AuthService.java:85-159` |
| User và repository identity | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/entity/User.java:187-224`; `repository/UserRepository.java:167-170` |
| JWT | `source/recruit_system/backend/common/src/main/java/recruit/demo/security/JwtService.java:268-315` |
| DTO | `source/recruit_system/backend/common/src/main/java/recruit/demo/dto/AuthDtos.java:474-509` |
| Provisioning sau xác thực | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/security/ProfileProvisioningFilter.java:631-639`; `service/ProfileProvisioningService.java:650-667` |
| Repositories provisioning | `source/recruit_system/backend/recruitment-service/src/main/java/recruit/demo/repository/CandidateProfileRepository.java:691-697`; `RecruiterProfileRepository.java:722-739`; `CompanyRepository.java:705-711` |

## Mâu thuẫn và giới hạn

- Theo quyết định đã chốt, biểu đồ theo kiến trúc microservices trong source. Không có mâu thuẫn cụ thể với tài liệu repo được đọc; `Module3_Interview_Flow.md` nói về phỏng vấn, không phải M1. Báo cáo PDF không có trên đĩa nên không đối chiếu.
- ACT M1 mô tả tra cứu principal ở recruitment-service qua `GET /internal/users/{id}`. Trong source, request đó thực hiện bởi `RemotePrincipalLookup` → `ServiceHttpClient` và identity-service cung cấp `InternalUserController`; các lớp này cùng `JwtAuthenticationFilter` không được liệt kê vì giới hạn 18 lớp. Tương tự, ba entity profile/company không được liệt kê để dành chỗ cho các lớp luồng đăng ký và provisioning. Đây là lược giản biểu đồ, không phải thiếu bằng chứng về lời gọi.
- Mỗi phần tử và quan hệ được truy vết trong thuộc tính `src` của spec. `PrincipalLookup` và các triển khai tra cứu không đưa vào do giới hạn số lớp; quan hệ phụ thuộc abstraction của `JwtAuthenticationFilter` vì vậy chỉ được ghi nhận trong ghi chú pattern, không vẽ thành cạnh. Không có open question còn treo từ phạm vi ACT được chuyển sang biểu đồ này.
