# Tasks: Hoàn thiện luồng xác thực

**Input**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), [contracts/auth-api.md](contracts/auth-api.md)
**Tests**: có (unit test cho logic bảo mật, theo Constitution III)

Định dạng: `[ID] [P?] [Story] Mô tả`. `[P]` = làm song song được (khác file, không phụ thuộc).

## Phase 1: Setup

- [x] T001 Thêm `spring-boot-starter-data-redis` vào `backend/common/pom.xml`; `spring-boot-starter-mail` vào `backend/identity-service/pom.xml`
- [x] T002 [P] Thêm service `redis` (redis:7) và `mailpit` vào `docker-compose.yml`; biến `REDIS_HOST` cho 3 service Java, `MAIL_HOST`/`MAIL_PORT`/`APP_FRONTEND_URL` cho identity; `depends_on` redis
- [x] T003 [P] Cấu hình `spring.data.redis` trong `application.yml` của identity, recruitment, interview; `spring.mail` + `app.auth.*` trong identity
- [x] T004 [P] Route `^/api/admin/users` → identity trong `infra/gateway/nginx.conf`; thêm biến mới vào `.env.microservices.example`

## Phase 2: Foundational (chặn mọi story)

- [x] T005 Migration `backend/identity-service/src/main/resources/db/migration/V4__auth_flow.sql` (4 cột, đánh dấu user cũ đã xác thực) và cập nhật entity `User`
- [x] T006 [P] Thêm mã lỗi 2003–2007 vào `backend/common/.../exception/ErrorCode.java`
- [x] T007 [P] `UserSnapshot` + `UserPrincipal` thêm `sessionsValidAfter` (giữ constructor cũ) trong `backend/common`
- [x] T008 `UserSnapshotCache` (Redis hash, TTL, nuốt lỗi Redis) trong `backend/common/.../security/`; `RemotePrincipalLookup` đọc cache trước
- [x] T009 `JwtAuthenticationFilter` từ chối token có `iat` < `sessionsValidAfter`; `CustomUserDetailsService` và `InternalUserController` trả mốc này; `InternalUserController` PATCH xoá cache
- [x] T010 [P] Unit test: filter từ chối token cũ, chấp nhận token mới (`backend/common/src/test/.../security/`)
- [x] T011 `AuthProperties` (`app.auth`), `OneTimeTokenService`, `LoginAttemptService`, `AuthMailService` trong identity-service
- [x] T012 [P] Unit test `OneTimeTokenService`, `LoginAttemptService` (mock `StringRedisTemplate`)
- [x] T013 `SecurityConfig` (common): permitAll cho `verify-email`, `resend-verification`, `forgot-password`, `reset-password`

## Phase 3: US1 – Đăng ký có xác thực email (P1) 🎯

- [x] T014 [US1] DTO mới trong `AuthDtos` (RegisterResponse, VerifyEmailRequest, EmailRequest, MessageResponse); quy tắc mật khẩu 8–100 có chữ và số
- [x] T015 [US1] `AuthService.register` không cấp token, cấp token xác thực + gửi mail; `verifyEmail`; `resendVerification`; endpoint trong `AuthController`
- [x] T016 [P] [US1] FE: `client.ts` (ApiError.code/data, authApi mới), `AuthContext` (register không đăng nhập, `verifyEmail`)
- [x] T017 [US1] FE: `RegisterPage` màn "kiểm tra email" + gửi lại; `VerifyEmailPage`; route `/verify-email`

## Phase 4: US2 – Đăng nhập + khoá tạm (P1)

- [x] T018 [US2] `AuthService.login`: kiểm tra khoá tạm → so mật khẩu (BCrypt giả khi không có user) → đếm sai / xoá đếm → chưa xác thực (2003) / bị khoá (2005)
- [x] T019 [P] [US2] Unit test `AuthService` cho login (đúng, sai, khoá tạm, chưa xác thực, bị khoá, email không tồn tại) và register / verify
- [x] T020 [US2] FE `LoginPage`: xử lý 2003 (nút gửi lại), 2004 (số phút), 2005; link "Quên mật khẩu?"

## Phase 5: US3 – Quên mật khẩu (P2)

- [x] T021 [US3] `AuthService.forgotPassword`, `resetPassword` (đổi mật khẩu, `sessions_valid_after`, xác thực email, gỡ khoá tạm, xoá cache); endpoint; unit test
- [x] T022 [US3] FE `ForgotPasswordPage`, `ResetPasswordPage`, route

## Phase 6: US4 – Admin khoá / mở khoá (P2)

- [x] T023 [US4] `UserRepository` tìm kiếm phân trang; `AdminUserService` (list, lock, unlock, chặn tự khoá / khoá admin, xoá cache); `AdminUserController` `/api/admin/users`
- [x] T024 [P] [US4] Unit test `AdminUserService`
- [x] T025 [US4] `AuthService.chooseRole` xoá cache sau khi đổi vai trò

## Phase 7: Polish

- [x] T026 `mvn test` toàn backend; FE `npm run lint` + `npm run build`
- [x] T027 E2E theo [quickstart.md](quickstart.md) với docker compose (build image identity, recruitment, interview)
- [x] T028 [P] Cập nhật `README.md` (Redis, Mailpit, biến môi trường, luồng auth)

## Dependencies

Setup → Foundational → US1 → US2 (cùng `AuthService`, làm tuần tự) → US3 → US4 → Polish. Các task FE (T016, T017, T020, T022) song song được với task backend cùng story sau khi contract đã chốt.
