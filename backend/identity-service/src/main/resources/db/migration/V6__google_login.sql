-- specs/005-google-login: liên kết tài khoản Google (subject "sub" của ID token Google, ổn định theo tài khoản).
ALTER TABLE users
    ADD COLUMN google_sub VARCHAR(64) NULL,
    ADD CONSTRAINT uq_users_google_sub UNIQUE (google_sub);
