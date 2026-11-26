-- specs/004-rbac: RBAC0. Role, Permission, ma trận Role→Permission. Gán user→role dùng users.role (mỗi user một role).
CREATE TABLE roles (
    code        VARCHAR(32)  NOT NULL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE permissions (
    code        VARCHAR(64)  NOT NULL PRIMARY KEY,
    resource    VARCHAR(32)  NOT NULL,
    description VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE role_permissions (
    role_code       VARCHAR(32) NOT NULL,
    permission_code VARCHAR(64) NOT NULL,
    PRIMARY KEY (role_code, permission_code),
    CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_code) REFERENCES roles (code) ON DELETE CASCADE,
    CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_code) REFERENCES permissions (code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO roles (code, name, description) VALUES
('CANDIDATE', 'Ứng viên', 'Tìm việc, tải CV, ứng tuyển, luyện phỏng vấn'),
('RECRUITER', 'Nhà tuyển dụng', 'Đăng tin, xem đơn ứng tuyển, xếp hạng ứng viên'),
('ADMIN', 'Quản trị viên', 'Quản trị người dùng, phân quyền; xem dữ liệu tuyển dụng');

INSERT INTO permissions (code, resource, description) VALUES
('cv:manage-own', 'cv', 'Tải, xem, sửa CV của mình'),
('application:apply', 'application', 'Nộp đơn ứng tuyển'),
('application:read-own', 'application', 'Xem đơn ứng tuyển của mình'),
('application:read-received', 'application', 'Xem đơn ứng tuyển vào tin của mình'),
('job:create', 'job', 'Đăng tin tuyển dụng'),
('job:update', 'job', 'Đổi trạng thái tin của mình'),
('job:read-own', 'job', 'Xem danh sách tin của mình'),
('matching:read-own', 'matching', 'Xem việc phù hợp với CV của mình'),
('matching:run', 'matching', 'Xếp hạng ứng viên cho tin của mình'),
('matching:run-pool', 'matching', 'Xếp hạng toàn bộ kho CV cho một tin'),
('matching:read-all', 'matching', 'Xem kết quả matching của mọi tin'),
('dashboard:recruiter', 'dashboard', 'Xem thống kê tuyển dụng'),
('question:read', 'interview', 'Xem ngân hàng câu hỏi'),
('interview:practice', 'interview', 'Tạo và làm phiên luyện phỏng vấn'),
('interview:read-result', 'interview', 'Xem kết quả phỏng vấn của ứng viên vào tin của mình'),
('interview:read-all', 'interview', 'Xem mọi phiên phỏng vấn'),
('user:read', 'user', 'Xem danh sách người dùng'),
('user:lock', 'user', 'Khoá / mở khoá tài khoản'),
('role:manage', 'role', 'Xem và sửa ma trận phân quyền');

INSERT INTO role_permissions (role_code, permission_code) VALUES
('CANDIDATE', 'cv:manage-own'), ('CANDIDATE', 'application:apply'), ('CANDIDATE', 'application:read-own'),
('CANDIDATE', 'matching:read-own'), ('CANDIDATE', 'interview:practice'),
('RECRUITER', 'job:create'), ('RECRUITER', 'job:update'), ('RECRUITER', 'job:read-own'),
('RECRUITER', 'application:read-received'), ('RECRUITER', 'matching:run'), ('RECRUITER', 'interview:read-result'),
('RECRUITER', 'dashboard:recruiter'), ('RECRUITER', 'question:read'),
('ADMIN', 'dashboard:recruiter'), ('ADMIN', 'question:read'), ('ADMIN', 'matching:read-all'),
('ADMIN', 'matching:run-pool'), ('ADMIN', 'interview:read-all'), ('ADMIN', 'user:read'), ('ADMIN', 'user:lock'),
('ADMIN', 'role:manage');

-- Gán user → role: users.role phải là một role đã khai báo.
ALTER TABLE users ADD CONSTRAINT fk_users_role FOREIGN KEY (role) REFERENCES roles (code);
