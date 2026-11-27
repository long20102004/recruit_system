package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** DTO chọn mẫu CV và xem trước CV chưa lưu cho ứng viên (specs/011-cv-templates). */
public final class CvTemplateSelectionDtos {

    private CvTemplateSelectionDtos() {
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SetTemplateRequest {
        private Integer templateId;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CvPreviewRequest {
        private Integer templateId;
        private String title;
        private CandidateProfileDto profile;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CvPreviewResult {
        private String html;
        private FileLinkDto pdfLink;
    }
}
