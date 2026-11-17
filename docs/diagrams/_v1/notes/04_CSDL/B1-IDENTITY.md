# B1-IDENTITY — Thiết kế CSDL identity-service

- Biểu đồ: ERD, phạm vi CSDL `hirelens_identity` của identity-service.
- Nguồn duy nhất cho cấu trúc: Flyway migrations `source/recruit_system/backend/identity-service/src/main/resources/db/migration/`, áp dụng theo thứ tự V1 → V3.
- Kiến trúc microservices: identity-service có CSDL riêng `hirelens_identity` (`docker-compose.yml:25`, JDBC tại `docker-compose.yml:83`).

## 1. Lược đồ cuối (V1 → V3)

| Migration | Nội dung |
|---|---|
| `V1__schema.sql:1` | Tạo bảng `users` (10 cột, CHECK role/status, UNIQUE email) |
| `V2__seed.sql` | INSERT 3 user mẫu + `ALTER TABLE users AUTO_INCREMENT = 4` — **bỏ qua** (dữ liệu mẫu, không phải cấu trúc) |
| `V3__role_chosen_once.sql:2` | Thêm cột `role_chosen TINYINT(1) NOT NULL DEFAULT 0` |

### Bảng `users`

| Cột | Kiểu SQL | Ràng buộc |
|---|---|---|
| id | INT AUTO_INCREMENT | PK |
| full_name | VARCHAR(255) | NOT NULL |
| email | VARCHAR(255) | NOT NULL, UNIQUE (`uq_users_email`) |
| password_hash | VARCHAR(255) | NOT NULL |
| phone | VARCHAR(50) | NULL |
| role | VARCHAR(32) | NOT NULL DEFAULT 'CANDIDATE', CHECK ∈ {CANDIDATE, RECRUITER, ADMIN} (`chk_users_role`) |
| role_chosen | TINYINT(1) | NOT NULL DEFAULT 0 (V3) |
| status | VARCHAR(32) | NOT NULL DEFAULT 'ACTIVE', CHECK ∈ {ACTIVE, INACTIVE, BANNED} (`chk_users_status`) |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

## 2. Quan hệ

- Không có FOREIGN KEY nào trong DDL của `hirelens_identity`, và bảng `users` không có cột `*_id` → **relations rỗng** (0 quan hệ, cả thật lẫn logical trong cùng CSDL).
- Tham chiếu chéo service (quy tắc: **không vẽ relation**, ghi note): `users.id` được tham chiếu bằng id từ các bảng thuộc `hirelens_recruitment`:
  - `candidate_profiles.user_id` → users.id
  - `recruiter_profiles.user_id` → users.id
  - `jobs.created_by` → users.id
  - (các Ref này chỉ còn trong `docs/schema.dbml:281,282,288`; các bảng đích đã chuyển sang recruitment-service)

## 3. Bảng truy vết

| Phần tử | Nguồn |
|---|---|
| entity `users` | `source/recruit_system/backend/identity-service/src/main/resources/db/migration/V1__schema.sql:1` |
| cột id … updated_at | `V1__schema.sql:2–10` |
| uq_users_email | `V1__schema.sql:13` |
| chk_users_role / chk_users_status | `V1__schema.sql:11–12` |
| cột role_chosen | `source/recruit_system/backend/identity-service/src/main/resources/db/migration/V3__role_chosen_once.sql:2` |
| CSDL hirelens_identity | `source/recruit_system/docker-compose.yml:25,83` |
| JPA entity User ↔ users | `source/recruit_system/backend/identity-service/src/main/java/recruit/demo/entity/User.java:10–17` (dùng cho E1, không vẽ trong ERD) |

## 4. Đối chiếu docs/schema.dbml với migration (mâu thuẫn / khác biệt)

1. **schema.dbml gộp nhầm bảng của service khác vào nhóm `nguoi_dung`:** TableGroup `nguoi_dung` gồm `users, candidate_profiles, companies, recruiter_profiles` (`schema.dbml:10–15`), nhưng `candidate_profiles`, `companies`, `recruiter_profiles` đã nằm ở `hirelens_recruitment` (recruitment-service `V1__schema.sql:1,103,113`). ERD này chỉ vẽ `users`. Các Ref `*.user_id > users.id` trong DBML là quan hệ liên service bằng id, không có FK thật — đúng tinh thần tiêu đề DBML "Cơ sở dữ liệu không còn khóa ngoại", nhưng trên ERD không vẽ relation, chỉ ghi note.
2. **schema.dbml thiếu ràng buộc CHECK:** DBML không thể hiện `chk_users_role`, `chk_users_status` (chỉ ghi trong note các giá trị enum). ERD lấy theo migration.
3. **schema.dbml ghi `updated_at datetime` (mặc định nullable)** — khớp DDL (`NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE`). Ngược lại, JPA entity `User.java:53` khai báo `updated_at nullable = false` — **mâu thuẫn nhỏ giữa entity và migration**; theo ưu tiên migration > entity, ERD vẽ nullable = true.
4. **DBML ghi chú tách CSDL ở lời bình luận header (`schema.dbml:1` "sau Flyway V6")** — đó là lược đồ thời monolith; hiện microservices tách 3 CSDL, migration của identity-service dừng ở V3. ERD vẽ theo identity-service migrations.

## 5. Open questions

- Không có.
