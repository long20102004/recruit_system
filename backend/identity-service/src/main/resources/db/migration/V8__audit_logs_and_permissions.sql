-- #12 Admin dashboard audit logs & new RBAC permissions for common features
CREATE TABLE audit_logs (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    event_type    VARCHAR(64)  NOT NULL,
    event_label   VARCHAR(120) NOT NULL,
    badge_class   VARCHAR(64)  NOT NULL DEFAULT 'badge b-brand',
    target        VARCHAR(255) NOT NULL,
    actor_user_id INT          NULL,
    actor_email   VARCHAR(255) NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_logs_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO permissions (code, resource, description) VALUES
('company:manage', 'company', 'Đăng ký và quản lý hồ sơ công ty'),
('company:approve', 'company', 'Duyệt, từ chối và khoá công ty'),
('job:moderate', 'job', 'Kiểm duyệt và khoá/mở khoá tin tuyển dụng'),
('dashboard:admin', 'dashboard', 'Xem tổng quan quản trị và nhật ký hoạt động'),
('application:update-status', 'application', 'Cập nhật trạng thái và ghi chú đơn ứng tuyển');

INSERT IGNORE INTO role_permissions (role_code, permission_code) VALUES
('RECRUITER', 'company:manage'),
('RECRUITER', 'application:update-status'),
('ADMIN', 'company:approve'),
('ADMIN', 'job:moderate'),
('ADMIN', 'dashboard:admin');
