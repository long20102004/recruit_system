ALTER TABLE match_cv_link
    ADD COLUMN suggestion_cv_hash VARCHAR(64),
    ADD COLUMN suggestion_catalog_hash VARCHAR(64);
