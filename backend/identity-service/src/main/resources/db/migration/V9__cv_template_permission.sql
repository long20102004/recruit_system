-- specs/011-cv-templates: quyền quản lý mẫu CV hệ thống
INSERT IGNORE INTO permissions (code, resource, description) VALUES
('cv-template:manage', 'cv-template', 'Quản lý mẫu CV hệ thống');

INSERT IGNORE INTO role_permissions (role_code, permission_code) VALUES
('ADMIN', 'cv-template:manage');
