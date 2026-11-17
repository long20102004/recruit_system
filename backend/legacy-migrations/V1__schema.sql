-- HireLens schema for MySQL: INT AUTO_INCREMENT + DATETIME + JSON

CREATE TABLE users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    phone           VARCHAR(50)  NULL,
    role            VARCHAR(32)  NOT NULL DEFAULT 'CANDIDATE',
    status          VARCHAR(32)  NOT NULL DEFAULT 'ACTIVE',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_users_role CHECK (role IN ('CANDIDATE', 'RECRUITER', 'ADMIN')),
    CONSTRAINT chk_users_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'BANNED')),
    CONSTRAINT uq_users_email UNIQUE (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
    CONSTRAINT uq_candidate_profiles_user UNIQUE (user_id),
    CONSTRAINT fk_candidate_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
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
    CONSTRAINT fk_recruiter_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
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
    CONSTRAINT fk_jobs_created_by FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT,
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

CREATE TABLE interview_questions (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    created_by       INT NULL,
    title            VARCHAR(255) NULL,
    question_text    TEXT NOT NULL,
    topic            VARCHAR(120) NULL,
    difficulty       VARCHAR(40) NULL,
    question_type    VARCHAR(40) NOT NULL DEFAULT 'TEXT',
    reference_answer TEXT NULL,
    max_score        DECIMAL(6, 2) NOT NULL DEFAULT 10.00,
    is_active        TINYINT(1) NOT NULL DEFAULT 1,
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_interview_questions_created_by FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE evaluation_rubrics (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    question_id           INT NOT NULL,
    criterion_name        VARCHAR(255) NOT NULL,
    criterion_description TEXT NULL,
    max_score             DECIMAL(6, 2) NULL,
    weight                DECIMAL(6, 4) NOT NULL DEFAULT 1.0000,
    expected_keywords     JSON NULL,
    created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_evaluation_rubrics_question FOREIGN KEY (question_id) REFERENCES interview_questions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE interview_sessions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id   INT NOT NULL,
    job_id         INT NULL,
    application_id INT NULL,
    title          VARCHAR(255) NULL,
    status         VARCHAR(32) NOT NULL DEFAULT 'CREATED',
    started_at     DATETIME NULL,
    completed_at   DATETIME NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_session_status CHECK (status IN ('CREATED', 'IN_PROGRESS', 'COMPLETED')),
    CONSTRAINT fk_interview_sessions_candidate FOREIGN KEY (candidate_id) REFERENCES candidate_profiles (id) ON DELETE CASCADE,
    CONSTRAINT fk_interview_sessions_job FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE SET NULL,
    CONSTRAINT fk_interview_sessions_application FOREIGN KEY (application_id) REFERENCES job_applications (id) ON DELETE SET NULL,
    INDEX idx_interview_sessions_candidate (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE interview_session_questions (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    session_id         INT NOT NULL,
    question_id        INT NOT NULL,
    question_order     INT NOT NULL,
    max_score          DECIMAL(6, 2) NOT NULL DEFAULT 10.00,
    time_limit_seconds INT NULL,
    CONSTRAINT uq_session_question_order UNIQUE (session_id, question_order),
    CONSTRAINT fk_session_questions_session FOREIGN KEY (session_id) REFERENCES interview_sessions (id) ON DELETE CASCADE,
    CONSTRAINT fk_session_questions_question FOREIGN KEY (question_id) REFERENCES interview_questions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE interview_responses (
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    session_question_id       INT NOT NULL,
    answer_text               TEXT NOT NULL,
    submitted_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_duration_seconds INT NULL,
    status                    VARCHAR(32) NOT NULL DEFAULT 'SUBMITTED',
    CONSTRAINT uq_interview_responses_sq UNIQUE (session_question_id),
    CONSTRAINT fk_interview_responses_sq FOREIGN KEY (session_question_id) REFERENCES interview_session_questions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE model_versions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    module_name VARCHAR(80) NOT NULL,
    model_name  VARCHAR(120) NOT NULL,
    version     VARCHAR(80) NOT NULL,
    model_path  VARCHAR(500) NULL,
    metrics     JSON NULL,
    is_active   TINYINT(1) NOT NULL DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_model_versions UNIQUE (module_name, model_name, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE evaluation_results (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    response_id         INT NOT NULL,
    evaluation_method   VARCHAR(40) NOT NULL DEFAULT 'RULE_BASED',
    bertscore_precision DECIMAL(6, 4) NULL,
    bertscore_recall    DECIMAL(6, 4) NULL,
    bertscore_f1        DECIMAL(6, 4) NULL,
    predicted_score     DECIMAL(6, 2) NOT NULL,
    human_score         DECIMAL(6, 2) NULL,
    correctness_score   DECIMAL(6, 2) NULL,
    completeness_score  DECIMAL(6, 2) NULL,
    feedback            TEXT NULL,
    strengths           JSON NULL,
    missing_points      JSON NULL,
    model_version_id    INT NULL,
    evaluated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_evaluation_results_response UNIQUE (response_id),
    CONSTRAINT fk_evaluation_results_response FOREIGN KEY (response_id) REFERENCES interview_responses (id) ON DELETE CASCADE,
    CONSTRAINT fk_evaluation_results_model FOREIGN KEY (model_version_id) REFERENCES model_versions (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
