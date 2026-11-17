INSERT INTO users (id, full_name, email, password_hash, phone, role, status) VALUES
(1, 'HireLens Admin', 'admin@hirelens.local', '$2b$10$5GqsimrjTQegLf02fjs9z.dJGb9OMxROXo3UxedUGROW7Lb3bcTDK', NULL, 'ADMIN', 'ACTIVE'),
(2, 'Nguyễn Minh An', 'candidate@hirelens.local', '$2b$10$5GqsimrjTQegLf02fjs9z.dJGb9OMxROXo3UxedUGROW7Lb3bcTDK', '0901234567', 'CANDIDATE', 'ACTIVE'),
(3, 'Trần Thu Hà', 'recruiter@hirelens.local', '$2b$10$5GqsimrjTQegLf02fjs9z.dJGb9OMxROXo3UxedUGROW7Lb3bcTDK', '0909876543', 'RECRUITER', 'ACTIVE');

ALTER TABLE users AUTO_INCREMENT = 4;
