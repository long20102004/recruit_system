INSERT INTO candidate_profiles (id, user_id, date_of_birth, address, headline, summary, years_of_experience, education_level) VALUES
(1, 2, '2003-05-12', 'Quận 1, TP. Hồ Chí Minh', 'Backend Developer',
 'Sinh viên năm cuối CNTT, có kinh nghiệm thực tập backend với Java/Spring Boot và MySQL.',
 2.5, 'Bachelor');

INSERT INTO companies (id, name, description, website, address) VALUES
(1, 'NovaTech', 'Công ty công nghệ xây dựng nền tảng HR và microservice.', 'https://novatech.example', 'Quận 1, TP.HCM'),
(2, 'AI Hub Vietnam', 'Lab AI tập trung NLP và Transformer.', 'https://aihub.example', 'Cầu Giấy, Hà Nội'),
(3, 'PixelWorks', 'Sản phẩm web end-to-end cho doanh nghiệp.', 'https://pixelworks.example', 'Remote toàn quốc'),
(4, 'FPT Software', 'Outsourcing và mentorship cho thực tập sinh Java.', 'https://fptsoftware.example', 'Quận 9, TP.HCM');

INSERT INTO recruiter_profiles (id, user_id, company_id, position) VALUES
(1, 3, 1, 'Talent Acquisition Lead');

INSERT INTO skills (id, name, category) VALUES
(1, 'Java', 'Language'),
(2, 'Spring Boot', 'Framework'),
(3, 'MySQL', 'Database'),
(4, 'REST API', 'Backend'),
(5, 'Python', 'Language'),
(6, 'Docker', 'DevOps'),
(7, 'NLP', 'AI'),
(8, 'BERT', 'AI'),
(9, 'React', 'Frontend'),
(10, 'Node.js', 'Backend'),
(11, 'TypeScript', 'Language'),
(12, 'Git', 'Tool'),
(13, 'SQL', 'Database'),
(14, 'PyTorch', 'AI'),
(15, 'Kafka', 'Messaging'),
(16, 'FastAPI', 'Framework');

INSERT INTO jobs (id, company_id, created_by, title, description, requirements, responsibilities, employment_type, work_location, salary_min, salary_max, currency, experience_required, status, posted_at) VALUES
(1, 1, 3, 'Junior Backend Developer (Java)',
 'Tham gia xây dựng microservice Java/Spring Boot, viết API và tối ưu truy vấn MySQL.',
 'Java, Spring Boot, MySQL, REST API',
 'Phát triển API, review code, tối ưu DB',
 'Hybrid', 'Quận 1, TP.HCM', 15000000, 22000000, 'VND', 1.0, 'PUBLISHED', DATE_SUB(NOW(), INTERVAL 2 HOUR)),
(2, 2, 3, 'NLP Engineer Intern',
 'Hỗ trợ pipeline trích xuất thông tin CV và đánh giá câu trả lời phỏng vấn bằng Transformer.',
 'Python, NLP, PyTorch',
 'Xây dựng pipeline NLP, thử nghiệm mô hình',
 'FULL_TIME', 'Cầu Giấy, Hà Nội', 5000000, 8000000, 'VND', 0, 'PUBLISHED', DATE_SUB(NOW(), INTERVAL 6 HOUR)),
(3, 3, 3, 'Full-stack Developer',
 'Phát triển sản phẩm web end-to-end cho nền tảng HR.',
 'React, Node.js, TypeScript, MySQL',
 'Phát triển frontend và backend',
 'REMOTE', 'Remote toàn quốc', 25000000, 35000000, 'VND', 2.0, 'PUBLISHED', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(4, 4, 3, 'Java Intern',
 'Thực tập Java, tham gia dự án outsourcing và mentorship.',
 'Java, SQL, Git',
 'Học và tham gia dự án dưới sự hướng dẫn',
 'FULL_TIME', 'Quận 9, TP.HCM', NULL, NULL, 'VND', 0, 'PUBLISHED', DATE_SUB(NOW(), INTERVAL 3 HOUR));

INSERT INTO job_skills (job_id, skill_id, is_required, minimum_years) VALUES
(1, 1, 1, 1), (1, 2, 1, 1), (1, 3, 1, 0.5), (1, 4, 1, 0.5), (1, 6, 0, NULL), (1, 15, 0, NULL),
(2, 5, 1, 0), (2, 7, 1, 0), (2, 14, 1, 0), (2, 8, 0, NULL), (2, 16, 0, NULL),
(3, 9, 1, 1), (3, 10, 1, 1), (3, 11, 1, 1), (3, 3, 1, 1),
(4, 1, 1, 0), (4, 13, 1, 0), (4, 12, 1, 0), (4, 2, 0, NULL);

INSERT INTO cv_documents (id, candidate_id, title, original_filename, file_url, file_type, file_size, parsing_status, is_default) VALUES
(1, 1, 'CV Nguyễn Minh An', 'CV_Nguyen_Minh_An.pdf', './uploads/seed/CV_Nguyen_Minh_An.pdf', 'application/pdf', 245760, 'COMPLETED', 1);

INSERT INTO cv_educations (cv_id, institution, degree, major, start_date, end_date, description) VALUES
(1, 'Đại học Công nghệ Thông tin', 'Cử nhân CNTT', 'Công nghệ thông tin', '2022-09-01', '2026-06-30', NULL);

INSERT INTO cv_experiences (cv_id, company_name, job_title, start_date, end_date, is_current, description) VALUES
(1, 'Công ty Demo Soft', 'Thực tập sinh Backend', '2025-06-01', '2025-12-31', 0,
 'Phát triển REST API bằng Spring Boot; thiết kế schema MySQL cho module tuyển dụng.');

INSERT INTO cv_projects (cv_id, project_name, role, start_date, end_date, description, project_url) VALUES
(1, 'Hệ thống tuyển dụng thông minh', 'Backend Developer', '2025-01-01', '2025-12-31',
 'Áp dụng NER, Embedding, Learning-to-Rank và BERTScore.', NULL);

INSERT INTO cv_skills (cv_id, skill_id, proficiency, years_experience, source) VALUES
(1, 1, 'Intermediate', 2.0, 'CV'), (1, 2, 'Intermediate', 1.5, 'CV'), (1, 3, 'Intermediate', 1.5, 'CV'),
(1, 4, 'Intermediate', 1.5, 'CV'), (1, 5, 'Basic', 1.0, 'CV'), (1, 12, 'Intermediate', 2.0, 'CV');

INSERT INTO cv_certificates (cv_id, certificate_name, issuing_organization, issue_date) VALUES
(1, 'AWS Cloud Practitioner (minh họa)', 'Amazon Web Services', '2025-03-01');

INSERT INTO matching_results (candidate_id, cv_id, job_id, semantic_score, skills_score, experience_score, overall_score, matched_skills, missing_skills, explanation, model_name, model_version) VALUES
(1, 1, 1, 0.8100, 1.0000, 0.9000, 0.8600,
 CAST('["Java","Spring Boot","MySQL","REST API"]' AS JSON),
 CAST('[]' AS JSON),
 'Khớp đầy đủ kỹ năng bắt buộc. Có kinh nghiệm Spring Boot / MySQL.',
 'hybrid-matcher', 'v0'),
(1, 1, 4, 0.6800, 1.0000, 0.8000, 0.7200,
 CAST('["Java","SQL","Git"]' AS JSON),
 CAST('[]' AS JSON),
 'Phù hợp vị trí Intern Java.',
 'hybrid-matcher', 'v0');

ALTER TABLE candidate_profiles AUTO_INCREMENT = 2;

ALTER TABLE companies AUTO_INCREMENT = 5;

ALTER TABLE recruiter_profiles AUTO_INCREMENT = 2;

ALTER TABLE skills AUTO_INCREMENT = 17;

ALTER TABLE jobs AUTO_INCREMENT = 5;

ALTER TABLE cv_documents AUTO_INCREMENT = 2;
