-- Backward-compatible row provenance for public-source KB snapshots.
ALTER TABLE skill ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE skill_alias ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE skill_edge ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE university ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE university_alias ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE job_title ADD COLUMN IF NOT EXISTS source TEXT;
