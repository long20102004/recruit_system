-- specs/008-r2-storage: logo/ảnh bìa công ty lưu trên bucket public R2 (object key).
-- cv_data.file_url và companies.license_file_url giữ cột, giá trị chuyển sang object key.
ALTER TABLE companies ADD COLUMN logo_key VARCHAR(512) NULL;
ALTER TABLE companies ADD COLUMN cover_key VARCHAR(512) NULL;
