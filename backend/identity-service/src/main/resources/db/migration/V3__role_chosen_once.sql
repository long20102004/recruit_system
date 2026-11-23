ALTER TABLE users
    ADD COLUMN role_chosen TINYINT(1) NOT NULL DEFAULT 0;

UPDATE users SET role_chosen = 1;
