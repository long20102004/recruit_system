-- Nhiều CV cho mỗi ứng viên (specs/007-multi-cv). Nội dung CV vẫn ở cv_data (field/value), nay gắn thêm cv_id.
-- Không khoá ngoài, theo quy ước V4; ứng dụng tự kiểm tra quyền sở hữu và giữ đúng 1 CV chính.

CREATE TABLE cv_documents (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT          NOT NULL,
    title        VARCHAR(255) NULL,
    is_main      TINYINT(1)   NOT NULL DEFAULT 0,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_cv_documents_candidate (candidate_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE cv_data ADD COLUMN cv_id INT NULL;

-- Dữ liệu cũ: mỗi ứng viên đang có cv_data thành 1 CV chính.
INSERT INTO cv_documents (candidate_id, title, is_main)
SELECT DISTINCT candidate_id, NULL, 1 FROM cv_data;

UPDATE cv_data d
JOIN cv_documents c ON c.candidate_id = d.candidate_id
SET d.cv_id = c.id;

ALTER TABLE cv_data
    MODIFY cv_id INT NOT NULL,
    ADD INDEX idx_cv_data_cv_field (cv_id, field),
    ADD INDEX idx_cv_data_candidate_field (candidate_id, field);
