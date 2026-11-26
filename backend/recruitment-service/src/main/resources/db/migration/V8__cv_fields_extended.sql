-- Bổ sung field hồ sơ CV lấy từ CandidateProfile của Module 1: GitHub, Mô tả kinh nghiệm, Dự án, Giải thưởng, Ngoại ngữ.
-- Học vấn / Kinh nghiệm giữ dạng "a — b" và thêm chi tiết sau " | " (CvProfileMapper.DETAIL).
-- Dữ liệu cv_data cũ được ghi lại khi ứng viên lưu hoặc tải CV lần sau.
UPDATE setting
SET value = 'Họ tên,Email,Điện thoại,GitHub,Tóm tắt,Kỹ năng,Kỹ năng suy ra,Học vấn,Kinh nghiệm,Mô tả kinh nghiệm,Dự án,Chứng chỉ,Giải thưởng,Ngoại ngữ'
WHERE name = 'CV_FIELD';
