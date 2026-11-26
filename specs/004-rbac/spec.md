# Feature Specification: Phân quyền RBAC0 theo permission

**Branch**: `hocnv/rbac` · **Created**: 2026-11-26 · **Status**: Draft

**Input**: "Triển khai phân quyền chuẩn RBAC". Đã chốt với người dùng: ma trận Role → Permission lưu trong DB identity; ADMIN có quyền quản trị + xem (không đăng tin, không nộp đơn thay người khác); làm cả backend và frontend.

## Hiện trạng (trước khi làm)

- 20 lời gọi `SecurityUtils.requireRole(...)` rải trong 6 service; không có `@PreAuthorize`; không có khái niệm permission.
- 5 nhánh `if (role == ADMIN) return` cho ADMIN toàn quyền trên tin / matching / phiên phỏng vấn của mọi recruiter.
- Một số endpoint chỉ cần đăng nhập (vd `GET /api/interviews/questions`).
- FE chặn route theo role cố định, ADMIN được bỏ qua; `/me` không trả quyền.

## User Stories

1. **(P1) Hệ thống kiểm tra quyền theo permission.** Mỗi endpoint nghiệp vụ yêu cầu một permission; user không có permission nhận 403. Ma trận nằm ở một chỗ (DB), không rải trong code.
2. **(P1) Admin xem và sửa ma trận phân quyền.** Admin bật/tắt permission cho từng role; thay đổi có hiệu lực ở mọi service ngay ở request kế tiếp. Không thể tự gỡ quyền quản lý phân quyền của ADMIN.
3. **(P2) Giao diện theo quyền.** Sau đăng nhập FE biết danh sách permission; route và mục menu chỉ hiện khi có quyền; nút thao tác ẩn khi không có quyền.

## Functional Requirements

- **FR-001** Permission dạng `resource:action`; role CANDIDATE, RECRUITER, ADMIN; ma trận Role→Permission lưu ở `role_permissions`.
- **FR-002** Mỗi user một role (`users.role`, khoá ngoại tới `roles.code`).
- **FR-003** Mọi endpoint nghiệp vụ của identity, recruitment, interview khai báo permission yêu cầu; thiếu quyền → 403.
- **FR-004** Bỏ toàn bộ `requireRole` và nhánh bypass ADMIN; quyền xem toàn hệ thống của ADMIN là permission riêng (`*:read-all`).
- **FR-005** Kiểm tra quyền sở hữu tài nguyên (tin của mình, đơn / phiên của mình) giữ nguyên trong service.
- **FR-006** `/api/auth/me`, đăng nhập, xác thực email trả danh sách permission của user.
- **FR-007** API admin: xem ma trận + danh mục permission; thay toàn bộ permission của một role. Chỉ role có `role:manage`. Không cho bỏ `role:manage` khỏi ADMIN.
- **FR-008** Sửa ma trận xoá cache quyền ở mọi service (cache user Redis) để có hiệu lực ngay.
- **FR-009** FE: guard route theo permission, menu và nút theo permission; trang admin Người dùng và Phân quyền.

## Success Criteria

- **SC-001** 0 lời gọi `requireRole` và 0 nhánh `role == ADMIN` cấp quyền trong service.
- **SC-002** Với mỗi role, gọi endpoint ngoài quyền trả 403; trong quyền trả 2xx (E2E).
- **SC-003** Bỏ một permission khỏi role trên trang Phân quyền → request kế tiếp của user role đó bị 403, không cần đăng nhập lại.

## Assumptions / ngoài phạm vi

- Vai trò trong công ty (OWNER/MANAGER/…) để đợt RC-07…10.
- Không thêm `user_roles` (đa role) vì toàn hệ thống giả định một role / user; thêm khi cần.
- ADMIN không có trang tổng hợp toàn hệ thống đợt này (danh sách tin/đơn của mọi công ty là task JB-10 / DB-02).
