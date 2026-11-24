-- Ket qua match cua cvmatch (plan I06). Dong cu giu engine = 'legacy'.
-- direction: jd_to_cv = recruiter xep hang ung vien cho mot job; cv_to_jd = goi y job cho ung vien.
-- Hai chieu tinh rieng (Luong C / D) nen luu rieng, khong de len nhau.
ALTER TABLE matching_results
    ADD COLUMN engine           VARCHAR(16) NOT NULL DEFAULT 'legacy',
    ADD COLUMN direction        VARCHAR(16) NULL,
    ADD COLUMN band             VARCHAR(8)  NULL,
    ADD COLUMN cap_applied      TINYINT(1)  NULL,
    ADD COLUMN flags            JSON        NULL,
    ADD COLUMN rank_position    INT         NULL,
    ADD COLUMN run_id           VARCHAR(64) NULL,
    ADD COLUMN cvmatch_cv_id    VARCHAR(64) NULL,
    ADD COLUMN explanation_json JSON        NULL,
    ADD INDEX idx_matching_results_job_engine (job_id, engine, direction),
    ADD INDEX idx_matching_results_candidate_engine (candidate_id, engine, direction);
