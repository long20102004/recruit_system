INSERT INTO interview_questions (external_key, title, question_text, topic, difficulty, question_type, reference_answer, skill, seniority, source, max_score, is_active) VALUES ('senior-web-sql-lock', 'SQL', 'Hai giao dịch cập nhật cùng hai bảng theo thứ tự ngược nhau. Bạn xử lý deadlock trong hệ thống đặt chỗ thế nào?', 'SQL', 'Hard', 'SCENARIO', 'Chuẩn hóa thứ tự khóa giữa các giao dịch, thu ngắn giao dịch và retry có giới hạn trên lỗi deadlock. Dùng khóa nghiệp vụ hoặc điều kiện cập nhật để giữ bất biến và đo tỷ lệ deadlock.', 'SQL', 'Senior', 'senior-bank', 10, TRUE);

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Thứ tự khóa nhất quán', 'Thứ tự khóa nhất quán', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Thứ tự khóa nhất quán') FROM interview_questions WHERE external_key = 'senior-web-sql-lock';

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Retry có giới hạn và giữ bất biến', 'Retry có giới hạn và giữ bất biến', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Retry có giới hạn và giữ bất biến') FROM interview_questions WHERE external_key = 'senior-web-sql-lock';

INSERT INTO interview_questions (external_key, title, question_text, topic, difficulty, question_type, reference_answer, skill, seniority, source, max_score, is_active) VALUES ('senior-web-api-retry', 'REST API', 'Thiết kế API tạo đơn ứng tuyển chịu được việc client gửi lại khi mất phản hồi.', 'REST API', 'Hard', 'APPLICATION', 'Dùng khóa idempotency gắn với người dùng và nội dung yêu cầu. Ghi khóa và dữ liệu nghiệp vụ trong cùng giao dịch, trả kết quả cũ nếu payload trùng và trả conflict khi khóa bị tái sử dụng với payload khác.', 'REST API', 'Senior', 'senior-bank', 10, TRUE);

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Phạm vi và kiểm tra khóa idempotency', 'Phạm vi và kiểm tra khóa idempotency', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Phạm vi và kiểm tra khóa idempotency') FROM interview_questions WHERE external_key = 'senior-web-api-retry';

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Ghi kết quả nguyên tử và xử lý xung đột', 'Ghi kết quả nguyên tử và xử lý xung đột', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Ghi kết quả nguyên tử và xử lý xung đột') FROM interview_questions WHERE external_key = 'senior-web-api-retry';

INSERT INTO interview_questions (external_key, title, question_text, topic, difficulty, question_type, reference_answer, skill, seniority, source, max_score, is_active) VALUES ('senior-web-spring-outbox', 'Spring Boot', 'Ứng dụng đã lưu đơn trong MySQL nhưng mất kết nối với broker ngay sau commit. Làm sao bảo đảm thông báo cuối cùng được gửi?', 'Spring Boot', 'Hard', 'SCENARIO', 'Ghi dữ liệu và bản ghi outbox trong cùng giao dịch. Publisher gửi lại cho đến khi nhận xác nhận, giữ mã sự kiện ổn định và dedup ở consumer. Theo dõi độ trễ và retry.', 'Spring Boot', 'Senior', 'senior-bank', 10, TRUE);

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Giao dịch nghiệp vụ và outbox', 'Giao dịch nghiệp vụ và outbox', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Giao dịch nghiệp vụ và outbox') FROM interview_questions WHERE external_key = 'senior-web-spring-outbox';

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Retry và idempotency phía consumer', 'Retry và idempotency phía consumer', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Retry và idempotency phía consumer') FROM interview_questions WHERE external_key = 'senior-web-spring-outbox';

INSERT INTO interview_questions (external_key, title, question_text, topic, difficulty, question_type, reference_answer, skill, seniority, source, max_score, is_active) VALUES ('senior-web-cache-stale', 'Java', 'Một cache hiển thị quyền cũ trong vài phút sau khi vai trò bị thu hồi. Bạn thiết kế đường đọc và cơ chế vô hiệu hóa thế nào?', 'Java', 'Hard', 'APPLICATION', 'Kiểm tra quyền nhạy cảm theo dữ liệu có thẩm quyền và vô hiệu cache theo phiên bản khi ghi. Đặt TTL ngắn làm lớp dự phòng, quan sát độ trễ, chọn fail-closed nếu nguồn quyền không truy cập được.', 'Java', 'Senior', 'senior-bank', 10, TRUE);

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Nguồn quyền có thẩm quyền', 'Nguồn quyền có thẩm quyền', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Nguồn quyền có thẩm quyền') FROM interview_questions WHERE external_key = 'senior-web-cache-stale';

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Vô hiệu hóa và xử lý lỗi an toàn', 'Vô hiệu hóa và xử lý lỗi an toàn', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Vô hiệu hóa và xử lý lỗi an toàn') FROM interview_questions WHERE external_key = 'senior-web-cache-stale';

INSERT INTO interview_questions (external_key, title, question_text, topic, difficulty, question_type, reference_answer, skill, seniority, source, max_score, is_active) VALUES ('senior-web-react-race', 'React', 'Người dùng đổi bộ lọc liên tục và kết quả request cũ ghi đè kết quả mới. Làm sao xử lý khi có phân trang và bộ nhớ đệm?', 'React', 'Hard', 'SCENARIO', 'Gắn mỗi request với khóa bộ lọc và trang, hủy hoặc bỏ kết quả request cũ, cập nhật cache theo đúng khóa. Kiểm thử phản hồi đến sai thứ tự và việc đổi bộ lọc trả trang về đầu.', 'React', 'Senior', 'senior-bank', 10, TRUE);

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Khóa dữ liệu theo bộ lọc và trang', 'Khóa dữ liệu theo bộ lọc và trang', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Khóa dữ liệu theo bộ lọc và trang') FROM interview_questions WHERE external_key = 'senior-web-react-race';

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Bỏ phản hồi cũ và kiểm thử điều kiện đua', 'Bỏ phản hồi cũ và kiểm thử điều kiện đua', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Bỏ phản hồi cũ và kiểm thử điều kiện đua') FROM interview_questions WHERE external_key = 'senior-web-react-race';

INSERT INTO interview_questions (external_key, title, question_text, topic, difficulty, question_type, reference_answer, skill, seniority, source, max_score, is_active) VALUES ('senior-web-observability', 'SQL', 'Truy vấn danh sách chậm đột ngột khi số dòng tăng. Bạn quyết định thêm chỉ mục dựa trên phép đo nào?', 'SQL', 'Hard', 'APPLICATION', 'Dùng EXPLAIN ANALYZE trên dữ liệu tương đồng production để so ước tính và số dòng thật. Xem độ chọn lọc, thứ tự cột và chi phí ghi của index; đo p95 và kiểm tra regression trước khi triển khai.', 'SQL', 'Senior', 'senior-bank', 10, TRUE);

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Đọc kế hoạch và độ chọn lọc', 'Đọc kế hoạch và độ chọn lọc', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Đọc kế hoạch và độ chọn lọc') FROM interview_questions WHERE external_key = 'senior-web-observability';

INSERT INTO evaluation_rubrics (question_id, criterion_name, criterion_description, max_score, weight, expected_keywords, reference_answers)
SELECT id, 'Đo trước sau với tải đại diện', 'Đo trước sau với tải đại diện', 5, 0.5, JSON_ARRAY(), JSON_ARRAY('Đo trước sau với tải đại diện') FROM interview_questions WHERE external_key = 'senior-web-observability';
