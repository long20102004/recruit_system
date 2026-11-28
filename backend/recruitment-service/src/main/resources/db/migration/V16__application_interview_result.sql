ALTER TABLE job_applications
    ADD COLUMN interview_score DECIMAL(5, 2),
    ADD COLUMN interview_completed_at DATETIME(6),
    ADD COLUMN interview_session_id INT;
