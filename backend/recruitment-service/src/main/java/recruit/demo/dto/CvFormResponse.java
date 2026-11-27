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
    /** CV đang xem; null khi ứng viên chưa có CV nào. */
    private Integer cvId;
    private String title;
    private boolean main;
    private String fileName;
    private String parsingStatus;
    private boolean analyzed;
    private List<CvFieldValue> fields;
    private CandidateProfileDto profile;
    private Integer templateId;
    private boolean hasGeneratedPdf;
    private String pdfError;
}
