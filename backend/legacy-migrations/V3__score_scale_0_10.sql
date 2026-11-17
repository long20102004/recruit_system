-- Align interview scoring with AI dataset scale (0–10)
UPDATE interview_questions SET max_score = 10.00 WHERE max_score IS NULL OR max_score < 10.00;
UPDATE interview_session_questions SET max_score = 10.00 WHERE max_score IS NULL OR max_score < 10.00;

-- Rubric criterion caps were on a 5-point sum; double to match 0–10
UPDATE evaluation_rubrics SET max_score = max_score * 2 WHERE max_score IS NOT NULL AND max_score <= 5.00;

ALTER TABLE interview_questions
    ALTER COLUMN max_score SET DEFAULT 10.00;
ALTER TABLE interview_session_questions
    ALTER COLUMN max_score SET DEFAULT 10.00;
