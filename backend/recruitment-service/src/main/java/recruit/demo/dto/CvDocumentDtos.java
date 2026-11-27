package recruit.demo.dto;

import java.time.LocalDateTime;
import java.util.List;

/** DTO cho danh sách và thao tác trên từng CV (/api/cvs/documents, specs/007-multi-cv). */
public final class CvDocumentDtos {

    private CvDocumentDtos() {
    }

    public record CvDocumentDto(
            Integer id,
            String title,
            String fileName,
            boolean main,
            String parsingStatus,
            boolean analyzed,
            List<String> skills,
            LocalDateTime updatedAt,
            boolean inActiveApplication
    ) {
    }

    /** Kết quả tải CV: id của CV vừa ghi và profile AI trích xuất được. */
    public record CvUploadResponse(Integer cvId, CandidateProfileDto profile) {
    }

    public record RenameCvRequest(String title) {
    }
}
