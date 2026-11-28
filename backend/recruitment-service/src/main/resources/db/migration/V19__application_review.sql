ALTER TABLE job_applications
    ADD COLUMN submitted_cv LONGTEXT,
    ADD COLUMN review_rating INT,
    ADD COLUMN review_note TEXT;
