-- specs/006-account-settings: hồ sơ cá nhân, đổi mật khẩu, cài đặt thông báo (màn C14).
ALTER TABLE users
    ADD COLUMN date_of_birth DATE        NULL,
    ADD COLUMN gender        VARCHAR(16) NULL,
    -- FALSE: tài khoản tạo bằng Google, chưa tự đặt mật khẩu (đổi mật khẩu không cần mật khẩu cũ).
    ADD COLUMN password_set  BOOLEAN     NOT NULL DEFAULT TRUE;

-- Chỉ lưu dòng người dùng đã đổi; loại không có dòng dùng mặc định trong NotificationType.
CREATE TABLE notification_preferences (
    user_id INT         NOT NULL,
    type    VARCHAR(40) NOT NULL,
    in_app  BOOLEAN     NOT NULL,
    email   BOOLEAN     NOT NULL,
    PRIMARY KEY (user_id, type),
    CONSTRAINT fk_notif_pref_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
