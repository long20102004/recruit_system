-- Dong bo CV / JD sang module match cvmatch (plan I05). Recruitment DB la nguon su that; cvmatch-db la du lieu dan
-- xuat, dung lai duoc tu cac bang nay (backfill). Khong khoa ngoai, theo quy uoc V4.

CREATE TABLE match_cv_link (
    candidate_id INT          NOT NULL PRIMARY KEY,
    cv_id        VARCHAR(64)  NULL,               -- do cvmatch sinh
    cv_version   INT          NULL,
    content_hash VARCHAR(64)  NULL,               -- SHA-256 JSON da gui thanh cong: khong gui lai khi khong doi
    status       VARCHAR(16)  NOT NULL,           -- PENDING | SYNCED | INVALID | FAILED | DELETED
    flags        TEXT         NULL,               -- JSON mang co cua cvmatch (low_content, no_identity...)
    last_error   TEXT         NULL,
    attempts     INT          NOT NULL DEFAULT 0,
    synced_at    DATETIME     NULL,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_match_cv_link_status (status),
    INDEX idx_match_cv_link_cv (cv_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE match_jd_link (
    job_id       INT          NOT NULL PRIMARY KEY,
    jd_id        VARCHAR(64)  NOT NULL,           -- "job-<id>"
    jd_version   INT          NULL,
    content_hash VARCHAR(64)  NULL,               -- noi dung JD khong tinh status (status di bang PATCH)
    jd_status    VARCHAR(16)  NULL,               -- open | draft | closed da gui
    status       VARCHAR(16)  NOT NULL,
    last_error   TEXT         NULL,
    attempts     INT          NOT NULL DEFAULT 0,
    synced_at    DATETIME     NULL,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_match_jd_link_jd (jd_id),
    INDEX idx_match_jd_link_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
