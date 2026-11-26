-- Common features (#1 Companies, #3 Applications, #4 Jobs lifecycle, #6 Saved jobs, #13 Job moderation)

-- #1: Expand companies table and add company_followers
ALTER TABLE companies
    ADD COLUMN legal_name           VARCHAR(255) NULL,
    ADD COLUMN display_name         VARCHAR(255) NULL,
    ADD COLUMN tax_code             VARCHAR(64)  NULL,
    ADD COLUMN industry             VARCHAR(120) NULL,
    ADD COLUMN company_size         VARCHAR(80)  NULL,
    ADD COLUMN company_type         VARCHAR(80)  NULL,
    ADD COLUMN founded_year         INT          NULL,
    ADD COLUMN city                 VARCHAR(120) NULL,
    ADD COLUMN headquarters         VARCHAR(500) NULL,
    ADD COLUMN office_address       VARCHAR(500) NULL,
    ADD COLUMN contact_email        VARCHAR(255) NULL,
    ADD COLUMN contact_phone        VARCHAR(64)  NULL,
    ADD COLUMN tagline              VARCHAR(500) NULL,
    ADD COLUMN short_bio            TEXT         NULL,
    ADD COLUMN why_work_here        TEXT         NULL,
    ADD COLUMN working_days         VARCHAR(120) NULL,
    ADD COLUMN overtime_policy      VARCHAR(120) NULL,
    ADD COLUMN tech_stack           TEXT         NULL,
    ADD COLUMN perks                TEXT         NULL,
    ADD COLUMN logo_file_name       VARCHAR(255) NULL,
    ADD COLUMN cover_file_name      VARCHAR(255) NULL,
    ADD COLUMN license_file_name    VARCHAR(255) NULL,
    ADD COLUMN license_file_meta    VARCHAR(120) NULL,
    ADD COLUMN license_file_url     VARCHAR(500) NULL,
    ADD COLUMN confirmed            TINYINT(1)   NOT NULL DEFAULT 0,
    ADD COLUMN status               VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE',
    ADD COLUMN reject_reason        TEXT         NULL,
    ADD COLUMN submitted_at         DATETIME     NULL,
    ADD COLUMN approved_at          DATETIME     NULL,
    ADD COLUMN submitted_by_user_id INT          NULL,
    ADD COLUMN submitted_by_label   VARCHAR(255) NULL,
    ADD COLUMN updated_at           DATETIME     NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ADD CONSTRAINT chk_companies_status CHECK (status IN ('DRAFT', 'PENDING', 'ACTIVE', 'REJECTED', 'LOCKED'));

CREATE TABLE company_followers (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    user_id    INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_company_followers UNIQUE (company_id, user_id),
    CONSTRAINT fk_company_followers_company FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
    INDEX idx_company_followers_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- #4 & #13: Expand jobs table status & fields
ALTER TABLE jobs DROP CHECK chk_jobs_status;
ALTER TABLE jobs
    ADD COLUMN level                       VARCHAR(64)  NULL,
    ADD COLUMN headcount                   INT          NULL,
    ADD COLUMN benefits                    TEXT         NULL,
    ADD COLUMN hot                         TINYINT(1)   NOT NULL DEFAULT 0,
    ADD COLUMN default_interview_questions INT          NULL DEFAULT 5,
    ADD COLUMN lock_reason                 VARCHAR(255) NULL,
    ADD COLUMN lock_note                   TEXT         NULL,
    ADD COLUMN locked_at                   DATETIME     NULL,
    ADD COLUMN locked_by                   INT          NULL,
    ADD CONSTRAINT chk_jobs_status CHECK (status IN ('DRAFT', 'PUBLISHED', 'CLOSED', 'EXPIRED', 'LOCKED'));

-- #3: Application status WITHDRAWN + history & internal notes
ALTER TABLE job_applications DROP CHECK chk_application_status;
ALTER TABLE job_applications
    ADD CONSTRAINT chk_application_status CHECK (status IN ('SUBMITTED', 'REVIEWING', 'INTERVIEW', 'REJECTED', 'HIRED', 'WITHDRAWN'));

CREATE TABLE application_status_history (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT          NOT NULL,
    from_status    VARCHAR(32)  NULL,
    to_status      VARCHAR(32)  NOT NULL,
    note           TEXT         NULL,
    actor_user_id  INT          NULL,
    actor_name     VARCHAR(255) NULL,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_app_hist_app FOREIGN KEY (application_id) REFERENCES job_applications (id) ON DELETE CASCADE,
    INDEX idx_app_hist_app (application_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE application_notes (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT      NOT NULL,
    rating         INT      NOT NULL DEFAULT 0,
    internal_note  TEXT     NULL,
    updated_by     INT      NULL,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_app_notes_app UNIQUE (application_id),
    CONSTRAINT fk_app_notes_app FOREIGN KEY (application_id) REFERENCES job_applications (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- #6: Saved jobs
CREATE TABLE saved_jobs (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT      NOT NULL,
    job_id       INT      NOT NULL,
    saved_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_saved_jobs UNIQUE (candidate_id, job_id),
    CONSTRAINT fk_saved_jobs_candidate FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (id) ON DELETE CASCADE,
    CONSTRAINT fk_saved_jobs_job FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
    INDEX idx_saved_jobs_candidate (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
