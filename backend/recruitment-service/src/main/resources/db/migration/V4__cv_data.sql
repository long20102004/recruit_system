-- One field/value table for CV content, plus a setting row that lists visible fields.
-- Foreign keys are removed; the application checks ownership and allowed fields.

CREATE TABLE setting (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(255) NOT NULL,
    value TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE cv_data (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT          NOT NULL,
    field        VARCHAR(255) NOT NULL,
    value        TEXT         NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO setting (name, value) VALUES
('CV_FIELD', 'Họ tên,Email,Điện thoại,Tóm tắt,Kỹ năng,Học vấn,Kinh nghiệm,Chứng chỉ');

INSERT INTO cv_data (candidate_id, field, value)
SELECT d.candidate_id, 'file_name', d.original_filename
FROM cv_documents d
JOIN (
    SELECT candidate_id, MAX(id) AS id
    FROM cv_documents
    GROUP BY candidate_id
) latest ON latest.id = d.id;

INSERT INTO cv_data (candidate_id, field, value)
SELECT d.candidate_id, 'file_url', d.file_url
FROM cv_documents d
JOIN (
    SELECT candidate_id, MAX(id) AS id
    FROM cv_documents
    GROUP BY candidate_id
) latest ON latest.id = d.id;

INSERT INTO cv_data (candidate_id, field, value)
SELECT d.candidate_id, 'parsing_status', d.parsing_status
FROM cv_documents d
JOIN (
    SELECT candidate_id, MAX(id) AS id
    FROM cv_documents
    GROUP BY candidate_id
) latest ON latest.id = d.id;

INSERT INTO cv_data (candidate_id, field, value)
SELECT cp.id, 'Họ tên', 'Nguyễn Minh An'
FROM candidate_profiles cp
WHERE EXISTS (SELECT 1 FROM cv_documents d WHERE d.candidate_id = cp.id);

INSERT INTO cv_data (candidate_id, field, value)
SELECT cp.id, 'Email', 'candidate@hirelens.local'
FROM candidate_profiles cp
WHERE EXISTS (SELECT 1 FROM cv_documents d WHERE d.candidate_id = cp.id);

INSERT INTO cv_data (candidate_id, field, value)
SELECT cp.id, 'Điện thoại', '0901234567'
FROM candidate_profiles cp
WHERE EXISTS (SELECT 1 FROM cv_documents d WHERE d.candidate_id = cp.id);

INSERT INTO cv_data (candidate_id, field, value)
SELECT cp.id, 'Tóm tắt', IFNULL(cp.summary, '')
FROM candidate_profiles cp
WHERE EXISTS (SELECT 1 FROM cv_documents d WHERE d.candidate_id = cp.id);

INSERT INTO cv_data (candidate_id, field, value)
SELECT d.candidate_id, 'Kỹ năng', GROUP_CONCAT(s.name ORDER BY s.name SEPARATOR ', ')
FROM cv_documents d
JOIN (
    SELECT candidate_id, MAX(id) AS id
    FROM cv_documents
    GROUP BY candidate_id
) latest ON latest.id = d.id
JOIN cv_skills cs ON cs.cv_id = d.id
JOIN skills s ON s.id = cs.skill_id
GROUP BY d.candidate_id;

INSERT INTO cv_data (candidate_id, field, value)
SELECT d.candidate_id, 'Học vấn',
       GROUP_CONCAT(CONCAT(IFNULL(e.degree, ''), ' — ', e.institution) SEPARATOR '\n')
FROM cv_documents d
JOIN (
    SELECT candidate_id, MAX(id) AS id
    FROM cv_documents
    GROUP BY candidate_id
) latest ON latest.id = d.id
JOIN cv_educations e ON e.cv_id = d.id
GROUP BY d.candidate_id;

INSERT INTO cv_data (candidate_id, field, value)
SELECT d.candidate_id, 'Kinh nghiệm',
       GROUP_CONCAT(CONCAT(e.job_title, ' @ ', IFNULL(e.company_name, '')) SEPARATOR '\n')
FROM cv_documents d
JOIN (
    SELECT candidate_id, MAX(id) AS id
    FROM cv_documents
    GROUP BY candidate_id
) latest ON latest.id = d.id
JOIN cv_experiences e ON e.cv_id = d.id
GROUP BY d.candidate_id;

INSERT INTO cv_data (candidate_id, field, value)
SELECT d.candidate_id, 'Chứng chỉ',
       GROUP_CONCAT(c.certificate_name ORDER BY c.certificate_name SEPARATOR ', ')
FROM cv_documents d
JOIN (
    SELECT candidate_id, MAX(id) AS id
    FROM cv_documents
    GROUP BY candidate_id
) latest ON latest.id = d.id
JOIN cv_certificates c ON c.cv_id = d.id
GROUP BY d.candidate_id;

ALTER TABLE job_applications DROP FOREIGN KEY fk_job_applications_cv;
ALTER TABLE matching_results DROP FOREIGN KEY fk_matching_results_cv;

DROP TABLE cv_certificates;
DROP TABLE cv_skills;
DROP TABLE cv_projects;
DROP TABLE cv_experiences;
DROP TABLE cv_educations;
DROP TABLE cv_documents;

ALTER TABLE recruiter_profiles DROP FOREIGN KEY fk_recruiter_profiles_company;
ALTER TABLE jobs DROP FOREIGN KEY fk_jobs_company;
ALTER TABLE job_skills DROP FOREIGN KEY fk_job_skills_job;
ALTER TABLE job_skills DROP FOREIGN KEY fk_job_skills_skill;
ALTER TABLE job_applications DROP FOREIGN KEY fk_job_applications_candidate;
ALTER TABLE job_applications DROP FOREIGN KEY fk_job_applications_job;
ALTER TABLE matching_results DROP FOREIGN KEY fk_matching_results_candidate;
ALTER TABLE matching_results DROP FOREIGN KEY fk_matching_results_job;
