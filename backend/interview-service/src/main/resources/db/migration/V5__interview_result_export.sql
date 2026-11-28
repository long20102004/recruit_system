ALTER TABLE interview_sessions
    ADD COLUMN completion_score DECIMAL(5, 2),
    ADD COLUMN result_exported_at DATETIME(6),
    ADD INDEX idx_interview_result_export (result_exported_at, id);

UPDATE interview_sessions target_session
JOIN (
    SELECT question.session_id, ROUND(AVG(evaluation.predicted_score), 2) AS score
    FROM interview_session_questions question
    JOIN interview_responses answer ON answer.session_question_id = question.id
    JOIN evaluation_results evaluation ON evaluation.response_id = answer.id
    GROUP BY question.session_id
) scored ON scored.session_id = target_session.id
SET target_session.completion_score = scored.score
WHERE target_session.status = 'COMPLETED' AND target_session.application_id IS NOT NULL
    AND target_session.job_id IS NOT NULL AND target_session.completed_at IS NOT NULL;

ALTER TABLE interview_responses
    ADD INDEX idx_interview_evaluation_queue (status, id);
