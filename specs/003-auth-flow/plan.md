# Implementation Plan: Hoàn thiện luồng xác thực

**Branch**: `hocnv/auth-flow` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-auth-flow/spec.md`

## Summary

Bổ sung vào identity-service: xác thực email khi đăng ký, khoá tạm khi đăng nhập sai nhiều lần, quên / đặt lại mật khẩu qua link email, admin khoá / mở khoá tài khoản. Redis giữ ba thứ có thời hạn: bộ đếm đăng nhập sai và khoá tạm, token dùng một lần (xác thực email, đặt lại mật khẩu, giãn cách gửi mail), và bản tóm tắt người dùng mà mọi service đọc khi xác thực JWT. Cột `sessions_valid_after` trong bảng `users` cho phép vô hiệu mọi JWT cũ khi khoá tài khoản hoặc đặt lại mật khẩu. Mail gửi qua SMTP; dev dùng Mailpit. Frontend thêm các màn xác thực email, quên mật khẩu, đặt lại mật khẩu và xử lý mã lỗi mới ở đăng nhập.

## Technical Context

**Language/Version**: Java 21 (Spring Boot 4.1.1), TypeScript / React 19 (Vite)
**Primary Dependencies**: thêm `spring-boot-starter-data-redis` (common), `spring-boot-starter-mail` (identity-service). Không thêm thư viện FE.
**Storage**: MySQL `hirelens_identity` (migration V4), Redis 7 (dữ liệu tạm, có TTL)
**Testing**: JUnit 5 + Mockito (`mvn test`), FE `npm run lint` + `npm run build`, E2E thủ công theo [quickstart.md](quickstart.md) với docker compose
**Target Platform**: Linux, docker compose
**Project Type**: Web application (backend microservices + frontend)
**Performance Goals**: xác thực JWT ở recruitment / interview không gọi identity khi cache còn (SC-006)
**Constraints**: không đổi hành vi đăng nhập của tài khoản seed; không lộ email có tồn tại; Redis hỏng không làm hỏng đăng nhập
**Scale/Scope**: 1 migration, ~10 file Java mới, ~8 file Java sửa, 3 trang FE mới, 3 trang FE sửa, compose + gateway

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Minimal Scope | Chỉ chạm identity-service, phần security / dto / exception của `common`, gateway, compose, các trang auth FE. Giao diện admin để ngoài phạm vi. Không đụng recruitment / interview ngoài cấu hình Redis. ✅ |
| II. Explicit Contracts | Có đổi hợp đồng: `POST /api/auth/register` không còn trả token; mật khẩu tối thiểu 8 ký tự; `UserSnapshot` thêm trường (tương thích ngược). Ghi rõ ở [contracts/auth-api.md](contracts/auth-api.md). FE là consumer duy nhất của register và được sửa cùng lúc. Smoke script chỉ dùng login của tài khoản seed nên không ảnh hưởng. ✅ |
| III. Proportionate Verification | Unit test cho AuthService, LoginAttemptService, OneTimeTokenService, AdminUserService, kiểm tra `sessions_valid_after` trong JwtAuthenticationFilter; `mvn test` toàn backend; FE lint + build; E2E bằng compose + Mailpit. ✅ |
| IV. CV Data Security | Token lưu dạng SHA-256, không log token / mật khẩu / link; phản hồi không lộ email tồn tại; giãn cách gửi mail. Secret SMTP qua biến môi trường. ✅ |
| V. Maintainable | Theo convention hiện có (`SecurityUtils.requireRole`, `BusinessException` + `ErrorCode`, Flyway). Hai dependency mới có lý do rõ (yêu cầu Redis, gửi mail). ✅ |

Không có vi phạm cần giải trình.

## Project Structure

### Documentation (this feature)

```text
specs/003-auth-flow/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/auth-api.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── common/src/main/java/recruit/demo/
│   ├── security/   JwtAuthenticationFilter (kiểm tra iat), UserPrincipal (+sessionsValidAfter),
│   │               RemotePrincipalLookup (đọc cache), UserSnapshotCache (mới)
│   ├── config/     SecurityConfig (permitAll endpoint mới)
│   ├── dto/        AuthDtos (request/response mới), ServiceDtos.UserSnapshot (+sessionsValidAfter)
│   └── exception/  ErrorCode (mã 2003–2007)
├── identity-service/src/main/
│   ├── java/recruit/demo/
│   │   ├── config/      AuthProperties (mới)
│   │   ├── controller/  AuthController (+4 endpoint), AdminUserController (mới), InternalUserController (evict cache)
│   │   ├── service/     AuthService, LoginAttemptService, OneTimeTokenService, AuthMailService, AdminUserService
│   │   ├── security/    CustomUserDetailsService (+sessionsValidAfter)
│   │   ├── entity/      User (+4 cột)
│   │   └── repository/  UserRepository (+tìm kiếm phân trang)
│   └── resources/       application.yml (redis, mail, app.auth), db/migration/V4__auth_flow.sql
├── recruitment-service, interview-service: application.yml (redis)
frontend/src/
├── api/client.ts            ApiError.code, authApi mới
├── context/AuthContext.tsx  register không đăng nhập; verifyEmail
├── pages/  LoginPage, RegisterPage (sửa); VerifyEmailPage, ForgotPasswordPage, ResetPasswordPage (mới)
└── App.tsx                  route mới
infra/gateway/nginx.conf     route /api/admin/users → identity
docker-compose.yml           redis, mailpit, biến môi trường
```

**Structure Decision**: Giữ cấu trúc microservice hiện có. Logic auth nằm ở identity-service; phần dùng chung cho mọi service (cache tóm tắt người dùng, kiểm tra JWT cũ) nằm ở `common`.

## Complexity Tracking

Không có.
