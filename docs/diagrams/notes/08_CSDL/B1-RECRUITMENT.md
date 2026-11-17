# B1-RECRUITMENT — Thiết kế CSDL recruitment-service

- **Biểu đồ:** Entity Relationship Diagram (ERD), phạm vi CSDL `hirelens_recruitment` của recruitment-service.
- **Nguồn duy nhất cho cấu trúc:** Flyway migrations `source/recruit_system/backend/recruitment-service/src/main/resources/db/migration/`, áp dụng tuần tự từ V1 → V5.
- **Kiến trúc:** Microservices độc lập, recruitment-service sở hữu CSDL riêng `hirelens_recruitment` (`docker-compose.yml:43`, JDBC cổng 3308 tại `docker-compose.yml:118`).

---

## 1. Lược đồ cuối (áp dụng V1 → V5)

### Quá trình tiến hóa schema:

| Migration | Loại | Nội dung |
|---|---|---|
| `V1__schema.sql:1–199` | DDL | Khởi tạo 14 bảng ban đầu: `candidate_profiles`, `cv_documents`, `cv_educations`, `cv_experiences`, `cv_projects`, `skills`, `cv_skills`, `cv_certificates`, `companies`, `recruiter_profiles`, `jobs`, `job_skills`, `job_applications`, `matching_results`. Thiết lập đầy đủ khóa chính PK, ràng buộc UNIQUE, CHECK và các FOREIGN KEY vật lý. |
| `V2__seed.sql:1–104` | DML | Chèn dữ liệu mẫu ban đầu (ứng viên, công ty, tin tuyển dụng, CV mẫu, đối sánh mẫu...) và cập nhật AUTO_INCREMENT — **bỏ qua** (dữ liệu mẫu, không thay đổi cấu trúc). |
| `V3__clear_seed_cv_matches.sql:1–5` | DML | Xóa dữ liệu mẫu đối sánh và CV nguyên mẫu (`DELETE FROM matching_results...`, `DELETE FROM cv_documents WHERE id = 1`) — **bỏ qua** (thao tác dữ liệu). |
| `V4__cv_data.sql:1–132` | DDL & DML | **Thay đổi cấu trúc cốt lõi:**<br>1. Tạo bảng `setting` (`id`, `name`, `value`) lưu cấu hình các trường CV (`V4:4–8`).<br>2. Tạo bảng `cv_data` (`id`, `candidate_id`, `field`, `value`) lưu dữ liệu trích xuất CV theo cặp trường/giá trị (`V4:10–15`).<br>3. Chuyển đổi dữ liệu từ các bảng CV cũ sang `cv_data`.<br>4. DROP khóa ngoại `fk_job_applications_cv` và `fk_matching_results_cv` (`V4:115–116`).<br>5. **DROP 6 bảng CV cũ:** `cv_certificates`, `cv_skills`, `cv_projects`, `cv_experiences`, `cv_educations`, `cv_documents` (`V4:118–123`).<br>6. **DROP toàn bộ 8 khóa ngoại vật lý còn lại** trong CSDL (`V4:125–132`), chuyển toàn bộ quan hệ trong CSDL sang quan hệ logic. |
| `V5__implied_skills_field.sql:1–4` | DML | Cập nhật cấu hình chuỗi trường `CV_FIELD` trong bảng `setting` để bổ sung mục "Kỹ năng suy ra" — **bỏ qua** (thao tác dữ liệu). |

### Kết quả: CSDL cuối cùng gồm đúng 10 bảng:
1. `candidate_profiles`
2. `companies`
3. `recruiter_profiles`
4. `skills`
5. `jobs`
6. `job_skills`
7. `job_applications`
8. `matching_results`
9. `setting`
10. `cv_data`

---

## 2. Chi tiết các thực thể (bảng)

### 2.1. `candidate_profiles`
Hồ sơ thông tin ứng viên (tạo khi người dùng có vai trò CANDIDATE).
- Nguồn: `V1__schema.sql:1–13`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Ràng buộc: `uq_candidate_profiles_user` UNIQUE (`user_id`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| user_id | INT | NOT NULL | — | True | — | ID tài khoản (`users.id` của identity-service) |
| date_of_birth | DATE | NULL | — | False | — | Ngày sinh |
| address | VARCHAR(500) | NULL | — | False | — | Địa chỉ |
| headline | VARCHAR(255) | NULL | — | False | — | Tiêu đề hồ sơ |
| summary | TEXT | NULL | — | False | — | Tóm tắt bản thân |
| years_of_experience | DECIMAL(4,1) | NULL | — | False | — | Số năm kinh nghiệm |
| education_level | VARCHAR(120) | NULL | — | False | — | Trình độ học vấn |
| created_at | DATETIME | NOT NULL | — | False | CURRENT_TIMESTAMP | Thời điểm tạo |
| updated_at | DATETIME | NULL | — | False | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Thời điểm cập nhật |

### 2.2. `companies`
Thông tin công ty / nhà tuyển dụng doanh nghiệp.
- Nguồn: `V1__schema.sql:103–111`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Ràng buộc: `uq_companies_name` UNIQUE (`name`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| name | VARCHAR(255) | NOT NULL | — | True | — | Tên công ty |
| description | TEXT | NULL | — | False | — | Mô tả công ty |
| website | VARCHAR(500) | NULL | — | False | — | Trang web |
| address | VARCHAR(500) | NULL | — | False | — | Địa chỉ trụ sở |
| created_at | DATETIME | NOT NULL | — | False | CURRENT_TIMESTAMP | Thời điểm tạo |

### 2.3. `recruiter_profiles`
Hồ sơ nhà tuyển dụng gắn với công ty.
- Nguồn: `V1__schema.sql:113–121`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Ràng buộc: `uq_recruiter_user_company` UNIQUE (`user_id`, `company_id`)
- Khóa ngoại cũ: `fk_recruiter_profiles_company` (đã bị DROP tại `V4__cv_data.sql:125`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| user_id | INT | NOT NULL | — | False | — | ID tài khoản (`users.id` của identity-service) |
| company_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `companies.id` |
| position | VARCHAR(255) | NULL | — | False | — | Chức vụ tại công ty |
| created_at | DATETIME | NOT NULL | — | False | CURRENT_TIMESTAMP | Thời điểm tạo |

### 2.4. `skills`
Danh mục kỹ năng chuẩn hóa trong hệ thống.
- Nguồn: `V1__schema.sql:72–77`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Ràng buộc: `uq_skills_name` UNIQUE (`name`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| name | VARCHAR(120) | NOT NULL | — | True | — | Tên kỹ năng (Java, Python, Docker...) |
| category | VARCHAR(80) | NULL | — | False | — | Phân loại (Language, Framework, Database...) |

### 2.5. `jobs`
Tin tuyển dụng công việc do nhà tuyển dụng đăng.
- Nguồn: `V1__schema.sql:123–147`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Ràng buộc CHECK: `chk_jobs_status` CHECK (`status IN ('DRAFT', 'PUBLISHED', 'CLOSED')`)
- Khóa ngoại cũ: `fk_jobs_company` (đã bị DROP tại `V4__cv_data.sql:126`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| company_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `companies.id` |
| created_by | INT | NOT NULL | — | False | — | ID tài khoản người tạo (`users.id` của identity-service) |
| title | VARCHAR(255) | NOT NULL | — | False | — | Tiêu đề công việc |
| description | TEXT | NULL | — | False | — | Mô tả công việc |
| requirements | TEXT | NULL | — | False | — | Yêu cầu ứng viên |
| responsibilities | TEXT | NULL | — | False | — | Trách nhiệm công việc |
| employment_type | VARCHAR(80) | NULL | — | False | — | Hình thức làm việc (Full-time, Hybrid, Remote...) |
| work_location | VARCHAR(255) | NULL | — | False | — | Địa điểm làm việc |
| salary_min | DECIMAL(14,2) | NULL | — | False | — | Mức lương tối thiểu |
| salary_max | DECIMAL(14,2) | NULL | — | False | — | Mức lương tối đa |
| currency | VARCHAR(16) | NOT NULL | — | False | 'VND' | Đơn vị tiền tệ |
| experience_required | DECIMAL(4,1) | NULL | — | False | — | Số năm kinh nghiệm yêu cầu |
| status | VARCHAR(32) | NOT NULL | — | False | 'DRAFT' | Trạng thái tin (`DRAFT`, `PUBLISHED`, `CLOSED`) |
| posted_at | DATETIME | NULL | — | False | — | Thời điểm đăng tin |
| deadline | DATETIME | NULL | — | False | — | Hạn chót ứng tuyển |
| created_at | DATETIME | NOT NULL | — | False | CURRENT_TIMESTAMP | Thời điểm tạo |
| updated_at | DATETIME | NULL | — | False | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Thời điểm cập nhật |

### 2.6. `job_skills`
Bảng liên kết kỹ năng yêu cầu cho từng tin tuyển dụng (quan hệ n-n giữa `jobs` và `skills`).
- Nguồn: `V1__schema.sql:149–158`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Ràng buộc: `uq_job_skills` UNIQUE (`job_id`, `skill_id`)
- Khóa ngoại cũ: `fk_job_skills_job`, `fk_job_skills_skill` (đã bị DROP tại `V4__cv_data.sql:127–128`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| job_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `jobs.id` |
| skill_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `skills.id` |
| is_required | TINYINT(1) | NOT NULL | — | False | 1 | 1 = bắt buộc, 0 = ưu tiên |
| minimum_years | DECIMAL(4,1) | NULL | — | False | — | Số năm kinh nghiệm tối thiểu yêu cầu |

### 2.7. `job_applications`
Đơn ứng tuyển của ứng viên vào vị trí tuyển dụng.
- Nguồn: `V1__schema.sql:160–176`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Ràng buộc CHECK: `chk_application_status` CHECK (`status IN ('SUBMITTED', 'REVIEWING', 'INTERVIEW', 'REJECTED', 'HIRED')`)
- Ràng buộc UNIQUE: `uq_job_applications` UNIQUE (`candidate_id`, `job_id`)
- Khóa ngoại cũ: `fk_job_applications_cv` (bị DROP tại `V4:115`), `fk_job_applications_candidate` và `fk_job_applications_job` (bị DROP tại `V4:129–130`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| candidate_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `candidate_profiles.id` |
| job_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `jobs.id` |
| cv_id | INT | NULL | — | False | — | Cột số lưu tham chiếu lịch sử, không còn bảng đích |
| status | VARCHAR(32) | NOT NULL | — | False | 'SUBMITTED' | Trạng thái ứng tuyển |
| cover_letter | TEXT | NULL | — | False | — | Thư ứng tuyển |
| applied_at | DATETIME | NOT NULL | — | False | CURRENT_TIMESTAMP | Thời điểm nộp đơn |
| updated_at | DATETIME | NULL | — | False | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Thời điểm cập nhật |

### 2.8. `matching_results`
Kết quả đối sánh tự động giữa hồ sơ ứng viên và tin tuyển dụng (thực hiện qua AI).
- Nguồn: `V1__schema.sql:178–199`
- Khóa chính: `id` (INT AUTO_INCREMENT)
- Khóa ngoại cũ: `fk_matching_results_cv` (bị DROP tại `V4:116`), `fk_matching_results_candidate` và `fk_matching_results_job` (bị DROP tại `V4:131–132`)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| candidate_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `candidate_profiles.id` |
| cv_id | INT | NULL | — | False | — | Cột số lưu tham chiếu lịch sử, không còn bảng đích |
| job_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `jobs.id` |
| semantic_score | DECIMAL(6,4) | NULL | — | False | — | Điểm tương đồng ngữ nghĩa |
| skills_score | DECIMAL(6,4) | NULL | — | False | — | Điểm trùng khớp kỹ năng |
| experience_score | DECIMAL(6,4) | NULL | — | False | — | Điểm kinh nghiệm |
| overall_score | DECIMAL(6,4) | NOT NULL | — | False | — | Điểm tổng hợp cuối cùng |
| matched_skills | JSON | NULL | — | False | — | Danh sách kỹ năng khớp (JSON array) |
| missing_skills | JSON | NULL | — | False | — | Danh sách kỹ năng còn thiếu (JSON array) |
| explanation | TEXT | NULL | — | False | — | Diễn giải kết quả đánh giá |
| model_name | VARCHAR(120) | NULL | — | False | — | Tên mô hình AI đối sánh |
| model_version | VARCHAR(120) | NULL | — | False | — | Phiên bản mô hình AI |
| created_at | DATETIME | NOT NULL | — | False | CURRENT_TIMESTAMP | Thời điểm tạo kết quả |

### 2.9. `setting`
Cấu hình linh hoạt của hệ thống tuyển dụng (danh mục trường hồ sơ CV_FIELD...).
- Nguồn: `V4__cv_data.sql:4–8`
- Khóa chính: `id` (INT AUTO_INCREMENT)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| name | VARCHAR(255) | NOT NULL | — | False | — | Tên cấu hình (ví dụ: `CV_FIELD`) |
| value | TEXT | NULL | — | False | — | Giá trị cấu hình (chuỗi CSV các trường hồ sơ) |

### 2.10. `cv_data`
Lưu trữ động các trường nội dung trích xuất từ CV của ứng viên (mô hình EAV đơn giản).
- Nguồn: `V4__cv_data.sql:10–15`
- Khóa chính: `id` (INT AUTO_INCREMENT)

| Cột | Kiểu SQL | Nullable | Khóa | Unique | Default | Ghi chú |
|---|---|---|---|---|---|---|
| id | INT | NOT NULL | PK | False | AUTO_INCREMENT | Khóa chính |
| candidate_id | INT | NOT NULL | FK (logical) | False | — | Tham chiếu `candidate_profiles.id` |
| field | VARCHAR(255) | NOT NULL | — | False | — | Tên trường (`file_name`, `file_url`, `parsing_status`, `Họ tên`, `Kỹ năng`...) |
| value | TEXT | NULL | — | False | — | Giá trị nội dung của trường |

---

## 3. Quan hệ (Relationships)

Theo quy định của `DIAGRAM_RULES.md` mục 4 và yêu cầu task:
1. **Quan hệ trong cùng CSDL:**
   - Tại migration `V4__cv_data.sql`, toàn bộ FOREIGN KEY vật lý ban đầu đã bị DROP hoàn toàn (`ALTER TABLE ... DROP FOREIGN KEY`).
   - Do đó, mọi quan hệ giữa các bảng trong cùng CSDL `hirelens_recruitment` đều là **quan hệ logic** (`logical: true`), kiểm tra tính toàn vẹn ở tầng dịch vụ Spring Boot.
   - Tổng cộng có **9 quan hệ logic**:
     1. `recruiter_profiles.company_id` → `companies.id` (`V1__schema.sql:116`)
     2. `jobs.company_id` → `companies.id` (`V1__schema.sql:125`)
     3. `job_skills.job_id` → `jobs.id` (`V1__schema.sql:151`)
     4. `job_skills.skill_id` → `skills.id` (`V1__schema.sql:152`)
     5. `job_applications.candidate_id` → `candidate_profiles.id` (`V1__schema.sql:162`)
     6. `job_applications.job_id` → `jobs.id` (`V1__schema.sql:163`)
     7. `matching_results.candidate_id` → `candidate_profiles.id` (`V1__schema.sql:180`)
     8. `matching_results.job_id` → `jobs.id` (`V1__schema.sql:182`)
     9. `cv_data.candidate_id` → `candidate_profiles.id` (`V4__cv_data.sql:12`)

2. **Tham chiếu chéo service (cross-service) — KHÔNG vẽ relation:**
   - `candidate_profiles.user_id` → `users.id` (CSDL `hirelens_identity` của identity-service).
   - `recruiter_profiles.user_id` → `users.id` (CSDL `hirelens_identity`).
   - `jobs.created_by` → `users.id` (CSDL `hirelens_identity`).
   - Không có quan hệ vật lý hay logic vẽ trên sơ đồ; chỉ ghi nhận tham chiếu qua ID.

3. **Tham chiếu lịch sử không còn bảng đích — KHÔNG vẽ relation:**
   - `job_applications.cv_id` và `matching_results.cv_id`: trước đây ở V1 trỏ tới `cv_documents.id`. Sau khi bảng `cv_documents` bị DROP ở V4, hai cột này được giữ lại dưới dạng số nguyên (`INT NULL`) phục vụ lưu vết lịch sử, không có bảng đích trong bất kỳ CSDL nào.

---

## 4. Bảng truy vết (Traceability Matrix)

| Phần tử | Nguồn định nghĩa | Ghi chú |
|---|---|---|
| Bảng `candidate_profiles` | `V1__schema.sql:1` | Cột tại dòng 2–11 |
| Bảng `companies` | `V1__schema.sql:103` | Cột tại dòng 104–109 |
| Bảng `recruiter_profiles` | `V1__schema.sql:113` | Cột tại dòng 114–118 |
| Bảng `skills` | `V1__schema.sql:72` | Cột tại dòng 73–75 |
| Bảng `jobs` | `V1__schema.sql:123` | Cột tại dòng 124–141 |
| Bảng `job_skills` | `V1__schema.sql:149` | Cột tại dòng 150–154 |
| Bảng `job_applications` | `V1__schema.sql:160` | Cột tại dòng 161–168 |
| Bảng `matching_results` | `V1__schema.sql:178` | Cột tại dòng 179–192 |
| Bảng `setting` | `V4__cv_data.sql:4` | Cột tại dòng 5–7 |
| Bảng `cv_data` | `V4__cv_data.sql:10` | Cột tại dòng 11–14 |
| DROP bảng `cv_*` | `V4__cv_data.sql:118–123` | Xóa 6 bảng CV cũ |
| DROP toàn bộ FOREIGN KEY | `V4__cv_data.sql:115–116, 125–132` | Loại bỏ toàn bộ FK vật lý |
| JPA Entities tương ứng | `recruit.demo.entity.*` | `CandidateProfile.java`, `Company.java`, `RecruiterProfile.java`, `Skill.java`, `Job.java`, `JobSkill.java`, `JobApplication.java`, `MatchingResult.java`, `Setting.java`, `CvData.java` |

---

## 5. Đối chiếu `docs/schema.dbml` với Migration (Mâu thuẫn / Khác biệt)

1. **Khớp về sự biến mất của khóa ngoại và bảng CV cũ:**
   - Tiêu đề `schema.dbml:3` ghi: *"Cơ sở dữ liệu không còn khóa ngoại. Các Ref bên dưới là quan hệ kiểm tra trong mã."* — Điều này khớp hoàn toàn với DDL tại `V4__cv_data.sql:115–132`.
   - `schema.dbml` không còn 6 bảng `cv_documents`, `cv_educations`, `cv_experiences`, `cv_projects`, `cv_skills`, `cv_certificates` mà đã có `setting` (`dbml:87–91`) và `cv_data` (`dbml:93–98`), khớp với kết quả sau Flyway V4.
   - `schema.dbml:149, 165` ghi rõ `cv_id` là *"Cột số, không còn bảng cv_documents"* và *"Cột số, không còn khóa tới hồ sơ"*.

2. **Khác biệt về phạm vi nhóm bảng (TableGroup vs Microservices):**
   - Trong `schema.dbml:10–15`, nhóm `nguoi_dung` gộp chung `users` với `candidate_profiles`, `companies`, `recruiter_profiles`. Tuy nhiên, trong kiến trúc microservices thực tế (theo `docker-compose.yml` và migration), bảng `users` thuộc CSDL `hirelens_identity` riêng, còn 3 bảng hồ sơ còn lại thuộc `hirelens_recruitment`. ERD này chỉ vẽ các bảng thuộc recruitment-service.
   - Các `Ref: *.user_id > users.id` trong DBML (`dbml:281, 282, 288`) là quan hệ liên service thông qua HTTP/ID, không thể có quan hệ CSDL.

3. **Thiếu sót ràng buộc CHECK trong `schema.dbml`:**
   - DBML không thể hiện các ràng buộc CHECK có trong DDL migration:
     - `chk_jobs_status`: `status IN ('DRAFT', 'PUBLISHED', 'CLOSED')` (`V1__schema.sql:142`)
     - `chk_application_status`: `status IN ('SUBMITTED', 'REVIEWING', 'INTERVIEW', 'REJECTED', 'HIRED')` (`V1__schema.sql:169`)
   - DBML chỉ ghi chú bằng note chứ không có định nghĩa ràng buộc. Spec ERD lấy chuẩn theo DDL migration.

4. **Giá trị cấu hình `CV_FIELD` trong `setting`:**
   - `schema.dbml:90` note: *"CV_FIELD: các mục hồ sơ, cách nhau bằng dấu phẩy"*.
   - Tại `V4__cv_data.sql:18`, seed 8 trường: `Họ tên,Email,Điện thoại,Tóm tắt,Kỹ năng,Học vấn,Kinh nghiệm,Chứng chỉ`.
   - Tại `V5__implied_skills_field.sql:2`, cấu hình được nâng cấp thành 9 trường: thêm `Kỹ năng suy ra`.

---

## 6. Open Questions

- **[cần xác nhận]** Cột `cv_id` trong hai bảng `job_applications` và `matching_results` được giữ lại từ schema V1 dưới dạng số nguyên (`INT NULL`) sau khi bảng `cv_documents` bị DROP ở V4. Hiện tại cả mã nguồn Java lẫn DDL đều không có bảng đích cho cột này. Trên ERD không vẽ quan hệ cho cột này.