# Plan: RBAC0 theo permission

## Ma trận ban đầu (seed `V5__rbac.sql`)

| Permission | Endpoint / dùng ở | CANDIDATE | RECRUITER | ADMIN |
|---|---|:-:|:-:|:-:|
| `cv:manage-own` | GET/POST/PUT `/api/cvs` | ✓ | | |
| `application:apply` | POST `/api/applications/jobs/{id}` | ✓ | | |
| `application:read-own` | GET `/api/applications/mine` | ✓ | | |
| `matching:read-own` | GET `/api/matching/mine`, POST `/mine/refresh`, giải thích (ứng viên), POST `/run` (ứng viên) | ✓ | | |
| `interview:practice` | tạo / làm / xem phiên của mình | ✓ | | |
| `job:create` | POST `/api/jobs` | | ✓ | |
| `job:update` | PATCH `/api/jobs/{id}/status` (tin của mình) | | ✓ | |
| `job:read-own` | GET `/api/jobs/mine` | | ✓ | |
| `application:read-received` | GET `/api/applications/recruiter` | | ✓ | |
| `matching:run` | GET/POST `/api/matching/jobs/{id}…`, POST `/run`, giải thích (tin của mình) | | ✓ | |
| `interview:read-result` | xem phiên của ứng viên vào tin của mình | | ✓ | |
| `dashboard:recruiter` | GET `/api/dashboard/recruiter` | | ✓ | ✓ |
| `question:read` | GET `/api/interviews/questions` | | ✓ | ✓ |
| `matching:read-all` | xem matching của mọi tin | | | ✓ |
| `matching:run-pool` | xếp hạng toàn kho CV (`scope=pool`) | | | ✓ |
| `interview:read-all` | xem mọi phiên phỏng vấn | | | ✓ |
| `user:read` | GET `/api/admin/users` | | | ✓ |
| `user:lock` | PATCH `/api/admin/users/{id}/lock\|unlock` | | | ✓ |
| `role:manage` | `/api/admin/roles` | | | ✓ |

Endpoint công khai / chỉ cần đăng nhập (không permission): `/api/auth/*`, GET `/api/jobs`, GET `/api/jobs/{id}`, `/health`, `/internal/**` (service token).

## Thiết kế

- **identity**: bảng `roles`, `permissions`, `role_permissions`; FK `users.role → roles.code`. `RbacService` đọc ma trận (cache trong bộ nhớ, xoá khi sửa). `UserResponse` và `UserSnapshot` thêm `permissions`. API `GET /api/admin/roles`, `PUT /api/admin/roles/{code}/permissions`; sửa ma trận → xoá cache `auth:user:*`.
- **common**: `UserPrincipal` thêm `permissions`, authorities = `ROLE_X` + permission; `UserSnapshotCache` lưu thêm permissions, có `evictAll`; `SecurityUtils.hasPermission`.
- **3 service**: `@PreAuthorize` ở controller; bỏ `requireRole`; bypass ADMIN → `hasPermission("…:read-all")`. Rẽ nhánh theo loại người dùng (ứng viên / recruiter) trong cùng endpoint vẫn theo role, chỉ để chọn luồng, không để cấp quyền.
- **gateway**: route `/api/admin/roles/**` → identity.
- **FE**: `UserDto.permissions`, `can()`; `RequireAuth perm`; menu lọc theo quyền; trang `/admin/users`, `/admin/roles`.

## Kiểm thử

Unit: ánh xạ authorities, method security với `@PreAuthorize`, `RbacService` (chặn gỡ `role:manage` của ADMIN). E2E Docker: ma trận 3 role × endpoint, sửa ma trận có hiệu lực ngay.
