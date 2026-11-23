-- Demo seed for HireLens (password for all users: demo1234)
-- BCrypt: $2b$10$5GqsimrjTQegLf02fjs9z.dJGb9OMxROXo3UxedUGROW7Lb3bcTDK
-- MySQL-compatible (no setval, no ::jsonb)

INSERT INTO users (id, full_name, email, password_hash, phone, role, status) VALUES
(1, 'HireLens Admin', 'admin@hirelens.local', '$2b$10$5GqsimrjTQegLf02fjs9z.dJGb9OMxROXo3UxedUGROW7Lb3bcTDK', NULL, 'ADMIN', 'ACTIVE'),
(2, 'Nguyễn Minh An', 'candidate@hirelens.local', '$2b$10$5GqsimrjTQegLf02fjs9z.dJGb9OMxROXo3UxedUGROW7Lb3bcTDK', '0901234567', 'CANDIDATE', 'ACTIVE'),
(3, 'Trần Thu Hà', 'recruiter@hirelens.local', '$2b$10$5GqsimrjTQegLf02fjs9z.dJGb9OMxROXo3UxedUGROW7Lb3bcTDK', '0909876543', 'RECRUITER', 'ACTIVE');

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

INSERT INTO interview_questions (id, created_by, title, question_text, topic, difficulty, question_type, reference_answer, max_score, is_active) VALUES
(1, 1, 'Spring Boot basics',
 'Spring Boot là gì và khác Spring Framework ở điểm nào?',
 'Spring Boot', 'Easy', 'TEXT',
 'Spring Boot dựa trên Spring Framework, cung cấp auto-configuration, starter dependencies và embedded server để khởi tạo ứng dụng nhanh hơn.',
 10.0, 1),
(2, 1, 'Dependency Injection',
 'Dependency Injection (DI) trong Spring hoạt động như thế nào?',
 'Dependency Injection', 'Medium', 'TEXT',
 'DI là IoC: Spring tiêm dependency thay vì tự new. Có constructor, setter và field injection; ưu tiên constructor injection.',
 10.0, 1),
(3, 1, 'REST API',
 'REST API là gì? Nêu một số HTTP method thường dùng.',
 'REST API', 'Easy', 'TEXT',
 'REST là kiến trúc dựa trên tài nguyên và HTTP. Các method phổ biến: GET, POST, PUT, PATCH, DELETE.',
 10.0, 1),
(4, 1, 'MySQL indexing',
 'Khi nào nên tạo index trên MySQL?',
 'MySQL', 'Medium', 'TEXT',
 'Tạo index cho cột thường dùng trong WHERE/JOIN để tăng tốc đọc, cân nhắc chi phí ghi và kích thước bảng.',
 10.0, 1);

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords) VALUES
(1, 'Auto-configuration', 'Nhắc tới auto-configuration / starter', 2.0, 0.4000, CAST('["auto-configuration","autoconfig","starter"]' AS JSON)),
(1, 'Embedded server', 'Nhắc tới embedded server', 1.5, 0.3000, CAST('["embedded","tomcat","jetty"]' AS JSON)),
(1, 'Based on Spring', 'Dựa trên Spring Framework', 1.5, 0.3000, CAST('["spring framework","dựa trên"]' AS JSON)),
(2, 'IoC idea', 'Ý tưởng IoC / tiêm dependency', 2.0, 0.4000, CAST('["ioc","tiêm","không tự new"]' AS JSON)),
(2, 'Constructor injection', 'Constructor injection', 1.5, 0.3000, CAST('["constructor"]' AS JSON)),
(2, 'Autowired / field', '@Autowired / field injection', 1.5, 0.3000, CAST('["autowired","field"]' AS JSON)),
(3, 'Resource-based', 'REST dựa trên tài nguyên', 2.0, 0.4000, CAST('["resource","tài nguyên"]' AS JSON)),
(3, 'HTTP methods', 'Các HTTP method phổ biến', 3.0, 0.6000, CAST('["get","post","put","delete"]' AS JSON)),
(4, 'WHERE/JOIN usage', 'Index cho WHERE/JOIN', 2.5, 0.5000, CAST('["where","join"]' AS JSON)),
(4, 'Write cost tradeoff', 'Chi phí ghi khi có index', 2.5, 0.5000, CAST('["ghi","write","chi phí"]' AS JSON));

INSERT INTO model_versions (module_name, model_name, version, model_path, metrics, is_active) VALUES
('matching', 'hybrid-matcher', 'v0', NULL, CAST('{"tfidf":true,"semantic":"stub"}' AS JSON), 1),
('interview', 'rule-based-eval', 'v0', NULL, CAST('{"method":"RULE_BASED"}' AS JSON), 1),
('cv_ner', 'rule+ner-baseline', 'v0', NULL, CAST('{}' AS JSON), 0);

-- Reset AUTO_INCREMENT after explicit IDs
ALTER TABLE users AUTO_INCREMENT = 4;
ALTER TABLE candidate_profiles AUTO_INCREMENT = 2;
ALTER TABLE companies AUTO_INCREMENT = 5;
ALTER TABLE recruiter_profiles AUTO_INCREMENT = 2;
ALTER TABLE skills AUTO_INCREMENT = 17;
ALTER TABLE jobs AUTO_INCREMENT = 5;
ALTER TABLE cv_documents AUTO_INCREMENT = 2;
ALTER TABLE interview_questions AUTO_INCREMENT = 5;
