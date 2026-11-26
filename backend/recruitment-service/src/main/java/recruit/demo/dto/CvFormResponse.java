package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/** Hồ sơ CV đã lưu (GET / PUT /api/cvs). profile: theo cấu trúc CandidateProfile (như /analyze-pdf); null khi chưa tải CV. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CvFormResponse {
    private String fileName;
    private String parsingStatus;
    private boolean analyzed;
    private List<CvFieldValue> fields;
    private CandidateProfileDto profile;
}
