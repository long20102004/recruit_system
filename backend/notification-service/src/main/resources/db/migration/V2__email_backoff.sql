-- specs/009: email lỗi chờ theo backoff (30s, 1m, 2m, 4m) thay vì thử lại mỗi 5 giây.
ALTER TABLE email_deliveries ADD COLUMN next_attempt_at TIMESTAMP NULL;
