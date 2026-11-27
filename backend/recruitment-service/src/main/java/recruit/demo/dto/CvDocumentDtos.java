package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

/** DTO cho danh sách và thao tác trên từng CV (/api/cvs/documents, specs/007-multi-cv). */
public final class CvDocumentDtos {

    private CvDocumentDtos() {
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CvDocumentDto {
        private Integer id;
        private String title;
        private String fileName;
        private boolean main;
        private String parsingStatus;
        private boolean analyzed;
        private List<String> skills;
        private LocalDateTime updatedAt;
        private boolean inActiveApplication;
    }

    /** Kết quả tải CV: id của CV vừa ghi và profile AI trích xuất được. */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CvUploadResponse {
        private Integer cvId;
        private CandidateProfileDto profile;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RenameCvRequest {
        private String title;
    }

    /** Body tạo CV trống; title tuỳ chọn. */
    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateCvRequest {
        private String title;
    }
}
