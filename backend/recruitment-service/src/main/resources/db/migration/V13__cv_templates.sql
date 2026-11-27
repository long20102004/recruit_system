-- specs/011-cv-templates: bảng mẫu CV (CONFIG/DOCX), cột template_id & generated_pdf trên cv_documents, seed 4 mẫu mặc định
CREATE TABLE cv_templates (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(80)  NOT NULL,
    type            VARCHAR(16)  NOT NULL,
    status          VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
    is_default      BOOLEAN      NOT NULL DEFAULT FALSE,
    config          JSON         NULL,
    docx_key        VARCHAR(512) NULL,
    preview_pdf_key VARCHAR(512) NULL,
    thumbnail_key   VARCHAR(512) NULL,
    created_by      INT          NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_cv_templates_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE cv_documents
    ADD COLUMN template_id INT NULL,
    ADD COLUMN generated_pdf_key VARCHAR(512) NULL,
    ADD COLUMN generated_at DATETIME NULL,
    ADD CONSTRAINT fk_cv_documents_template FOREIGN KEY (template_id) REFERENCES cv_templates (id) ON DELETE RESTRICT;

INSERT INTO cv_templates (name, type, status, is_default, config) VALUES
('Harvard', 'CONFIG', 'ACTIVE', TRUE,
 '{"layout":"ONE_COLUMN","font":"Tinos","accent":"#1f1d1a","background":"#ffffff","header":"CENTER","heading":"UPPERCASE_RULE","dates":"RIGHT_INLINE","density":"COMPACT","margin":"NORMAL","sections":["info","education","experience","projects","honours","skills","languages","certificates"]}'),
('Hiện đại 2 cột', 'CONFIG', 'ACTIVE', FALSE,
 '{"layout":"TWO_COLUMN","font":"Be Vietnam Pro","accent":"#2f4cb8","background":"#ffffff","header":"LEFT","heading":"ACCENT","dates":"BELOW","density":"NORMAL","margin":"NORMAL","sections":["info","skills","languages","certificates","objective","experience","projects","education","honours"]}'),
('Tối giản ATS', 'CONFIG', 'ACTIVE', FALSE,
 '{"layout":"ONE_COLUMN","font":"Inter","accent":"#1f1d1a","background":"#ffffff","header":"LEFT","heading":"PLAIN","dates":"RIGHT_INLINE","density":"NORMAL","margin":"NORMAL","sections":["info","objective","experience","education","projects","skills","certificates","languages","honours"]}'),
('Cổ điển', 'CONFIG', 'ACTIVE', FALSE,
 '{"layout":"ONE_COLUMN","font":"EB Garamond","accent":"#243a92","background":"#fffdf9","header":"CENTER","heading":"UPPERCASE_RULE","dates":"RIGHT_INLINE","density":"NORMAL","margin":"WIDE","sections":["info","objective","education","experience","projects","skills","honours","certificates","languages"]}');
