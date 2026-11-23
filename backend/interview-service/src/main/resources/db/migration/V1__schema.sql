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
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    candidate_user_id INT NOT NULL,
    job_title VARCHAR(255) NULL,
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
