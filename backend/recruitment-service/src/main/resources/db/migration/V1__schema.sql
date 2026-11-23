CREATE TABLE candidate_profiles (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    user_id              INT          NOT NULL,
    date_of_birth        DATE         NULL,
    address              VARCHAR(500) NULL,
    headline             VARCHAR(255) NULL,
    summary              TEXT         NULL,
    years_of_experience  DECIMAL(4, 1) NULL,
    education_level      VARCHAR(120) NULL,
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME     NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_candidate_profiles_user UNIQUE (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cv_documents (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id       INT          NOT NULL,
    title              VARCHAR(255) NULL,
    original_filename  VARCHAR(255) NOT NULL,
    file_url           VARCHAR(500) NOT NULL,
    file_type          VARCHAR(120) NULL,
    file_size          INT          NULL,
    extracted_text     TEXT         NULL,
    parsing_status     VARCHAR(32)  NOT NULL DEFAULT 'PENDING',
    is_default         TINYINT(1)   NOT NULL DEFAULT 0,
    uploaded_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME     NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_cv_parsing_status CHECK (parsing_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    CONSTRAINT fk_cv_documents_candidate FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (id) ON DELETE CASCADE,
    INDEX idx_cv_documents_candidate (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cv_educations (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    cv_id        INT NOT NULL,
    institution  VARCHAR(255) NOT NULL,
    degree       VARCHAR(255) NULL,
    major        VARCHAR(255) NULL,
    start_date   DATE NULL,
    end_date     DATE NULL,
    description  TEXT NULL,
    CONSTRAINT fk_cv_educations_cv FOREIGN KEY (cv_id) REFERENCES cv_documents (id) ON DELETE CASCADE,
    INDEX idx_cv_educations_cv (cv_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cv_experiences (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    cv_id         INT NOT NULL,
    company_name  VARCHAR(255) NULL,
    job_title     VARCHAR(255) NOT NULL,
    start_date    DATE NULL,
    end_date      DATE NULL,
    is_current    TINYINT(1) NOT NULL DEFAULT 0,
    description   TEXT NULL,
    CONSTRAINT fk_cv_experiences_cv FOREIGN KEY (cv_id) REFERENCES cv_documents (id) ON DELETE CASCADE,
    INDEX idx_cv_experiences_cv (cv_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cv_projects (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    cv_id         INT NOT NULL,
    project_name  VARCHAR(255) NOT NULL,
    role          VARCHAR(255) NULL,
    start_date    DATE NULL,
    end_date      DATE NULL,
    description   TEXT NULL,
    project_url   VARCHAR(500) NULL,
    CONSTRAINT fk_cv_projects_cv FOREIGN KEY (cv_id) REFERENCES cv_documents (id) ON DELETE CASCADE,
    INDEX idx_cv_projects_cv (cv_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE skills (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(120) NOT NULL,
    category VARCHAR(80) NULL,
    CONSTRAINT uq_skills_name UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cv_skills (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    cv_id            INT NOT NULL,
    skill_id         INT NOT NULL,
    proficiency      VARCHAR(50) NULL,
    years_experience DECIMAL(4, 1) NULL,
    source           VARCHAR(40) NOT NULL DEFAULT 'CV',
    CONSTRAINT uq_cv_skills UNIQUE (cv_id, skill_id),
    CONSTRAINT fk_cv_skills_cv FOREIGN KEY (cv_id) REFERENCES cv_documents (id) ON DELETE CASCADE,
    CONSTRAINT fk_cv_skills_skill FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cv_certificates (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    cv_id                INT NOT NULL,
    certificate_name     VARCHAR(255) NOT NULL,
    issuing_organization VARCHAR(255) NULL,
    issue_date           DATE NULL,
    expiry_date          DATE NULL,
    credential_url       VARCHAR(500) NULL,
    CONSTRAINT fk_cv_certificates_cv FOREIGN KEY (cv_id) REFERENCES cv_documents (id) ON DELETE CASCADE,
    INDEX idx_cv_certificates_cv (cv_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE companies (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    description TEXT NULL,
    website     VARCHAR(500) NULL,
    address     VARCHAR(500) NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_companies_name UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE recruiter_profiles (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    company_id INT NOT NULL,
    position   VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_recruiter_user_company UNIQUE (user_id, company_id),
    CONSTRAINT fk_recruiter_profiles_company FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE jobs (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    company_id           INT NOT NULL,
    created_by           INT NOT NULL,
    title                VARCHAR(255) NOT NULL,
    description          TEXT NULL,
    requirements         TEXT NULL,
    responsibilities     TEXT NULL,
    employment_type      VARCHAR(80) NULL,
    work_location        VARCHAR(255) NULL,
    salary_min           DECIMAL(14, 2) NULL,
    salary_max           DECIMAL(14, 2) NULL,
    currency             VARCHAR(16) NOT NULL DEFAULT 'VND',
    experience_required  DECIMAL(4, 1) NULL,
    status               VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    posted_at            DATETIME NULL,
    deadline             DATETIME NULL,
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_jobs_status CHECK (status IN ('DRAFT', 'PUBLISHED', 'CLOSED')),
    CONSTRAINT fk_jobs_company FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
    INDEX idx_jobs_status (status),
    INDEX idx_jobs_work_location (work_location),
    INDEX idx_jobs_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE job_skills (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    job_id        INT NOT NULL,
    skill_id      INT NOT NULL,
    is_required   TINYINT(1) NOT NULL DEFAULT 1,
    minimum_years DECIMAL(4, 1) NULL,
    CONSTRAINT uq_job_skills UNIQUE (job_id, skill_id),
    CONSTRAINT fk_job_skills_job FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
    CONSTRAINT fk_job_skills_skill FOREIGN KEY (skill_id) REFERENCES skills (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE job_applications (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NOT NULL,
    job_id       INT NOT NULL,
    cv_id        INT NULL,
    status       VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED',
    cover_letter TEXT NULL,
    applied_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_application_status CHECK (status IN ('SUBMITTED', 'REVIEWING', 'INTERVIEW', 'REJECTED', 'HIRED')),
    CONSTRAINT uq_job_applications UNIQUE (candidate_id, job_id),
    CONSTRAINT fk_job_applications_candidate FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (id) ON DELETE CASCADE,
    CONSTRAINT fk_job_applications_job FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
    CONSTRAINT fk_job_applications_cv FOREIGN KEY (cv_id) REFERENCES cv_documents (id) ON DELETE SET NULL,
    INDEX idx_job_applications_candidate (candidate_id),
    INDEX idx_job_applications_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE matching_results (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id     INT NOT NULL,
    cv_id            INT NULL,
    job_id           INT NOT NULL,
    semantic_score   DECIMAL(6, 4) NULL,
    skills_score     DECIMAL(6, 4) NULL,
    experience_score DECIMAL(6, 4) NULL,
    overall_score    DECIMAL(6, 4) NOT NULL,
    matched_skills   JSON NULL,
    missing_skills   JSON NULL,
    explanation      TEXT NULL,
    model_name       VARCHAR(120) NULL,
    model_version    VARCHAR(120) NULL,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_matching_results_candidate FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (id) ON DELETE CASCADE,
    CONSTRAINT fk_matching_results_cv FOREIGN KEY (cv_id) REFERENCES cv_documents (id) ON DELETE SET NULL,
    CONSTRAINT fk_matching_results_job FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
    INDEX idx_matching_results_cv_job_created (cv_id, job_id, created_at),
    INDEX idx_matching_results_candidate (candidate_id),
    INDEX idx_matching_results_job (job_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
