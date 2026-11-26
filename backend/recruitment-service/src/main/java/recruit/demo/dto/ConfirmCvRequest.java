package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * Body của PUT /api/cvs.
 * profile (tuỳ chọn): hồ sơ đã sửa theo cấu trúc CandidateProfile; backend tự ghi lại các field dùng cho matching.
 * fields: ghi đè từng field sau đó (ví dụ "Kỹ năng suy ra"); client cũ chỉ gửi fields vẫn chạy như trước.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConfirmCvRequest {
    private List<CvFieldValue> fields;
    private CandidateProfileDto profile;
}
