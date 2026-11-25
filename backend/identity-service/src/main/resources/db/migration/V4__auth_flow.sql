-- specs/003-auth-flow: xác thực email, admin khoá tài khoản, vô hiệu phiên cũ.
ALTER TABLE users
    ADD COLUMN email_verified_at    DATETIME     NULL,
    ADD COLUMN locked_reason        VARCHAR(500) NULL,
    ADD COLUMN locked_at            DATETIME     NULL,
    ADD COLUMN sessions_valid_after DATETIME     NULL;

-- Tài khoản có từ trước (gồm seed) coi như đã xác thực email.
UPDATE users SET email_verified_at = created_at WHERE email_verified_at IS NULL;
