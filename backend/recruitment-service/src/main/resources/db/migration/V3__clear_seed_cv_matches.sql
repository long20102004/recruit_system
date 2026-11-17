-- Seed CV and precomputed matches are prototype data.
-- Job suggestions appear only after a user uploads a CV that the system can analyze.

DELETE FROM matching_results WHERE candidate_id = 1 OR cv_id = 1;
DELETE FROM cv_documents WHERE id = 1;
