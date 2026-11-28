ALTER TABLE candidate_profiles
    ADD COLUMN is_open_for_job BOOLEAN NOT NULL DEFAULT FALSE,
    ADD INDEX idx_candidates_open_for_job (is_open_for_job, id);
