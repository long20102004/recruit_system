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

ALTER TABLE interview_questions AUTO_INCREMENT = 5;
