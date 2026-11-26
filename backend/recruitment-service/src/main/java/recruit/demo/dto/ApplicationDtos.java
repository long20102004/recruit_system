package recruit.demo.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import recruit.demo.enums.ApplicationStatus;

import java.time.LocalDateTime;
import java.util.List;

public final class ApplicationDtos {

    private ApplicationDtos() {
    }

    public record ApplyRequest(Integer cvDocumentId, String coverLetter) {
    }

    public record ApplicationResponse(
            Integer id,
            Integer jobId,
            String jobTitle,
            String companyName,
            Integer candidateId,
            String candidateName,
            Integer cvDocumentId,
            ApplicationStatus status,
            String coverLetter,
            LocalDateTime appliedAt,
            Integer matchScore
    ) {
        public ApplicationResponse(
                Integer id, Integer jobId, String jobTitle, String companyName,
                Integer candidateId, String candidateName, Integer cvDocumentId,
                ApplicationStatus status, String coverLetter, LocalDateTime appliedAt) {
            this(id, jobId, jobTitle, companyName, candidateId, candidateName,
                    cvDocumentId, status, coverLetter, appliedAt, null);
        }
    }

    public record UpdateApplicationStatusRequest(@NotBlank String status, String note) {
    }

    public record BulkUpdateStatusRequest(
            @NotEmpty List<Integer> applicationIds,
            @NotBlank String status,
            String note
    ) {
    }

    public record UpdateApplicationNoteRequest(
            @Min(0) @Max(5) int rating,
            String internalNote
    ) {
    }

    public record ApplicationExperienceItem(String title, String company, String period, String description) {
    }

    public record ApplicationCvDto(
            String roleTitle,
            String yearsExpLabel,
            String email,
            String phone,
            String summary,
            List<ApplicationExperienceItem> experiences,
            String education,
            List<String> matchedSkills,
            List<String> otherSkills
    ) {
    }

    public record MatchBreakdownItem(String label, int percent) {
    }

    public record ApplicationMatchDto(
            int overallPercent,
            List<MatchBreakdownItem> breakdown,
            List<String> missingSkills
    ) {
    }

    public record ApplicationHistoryDto(
            Integer id,
            String fromStatus,
            String toStatus,
            String statusLabel,
            LocalDateTime timestamp,
            String actor,
            String note
    ) {
    }

    public record ApplicationDetailResponse(
            Integer id,
            Integer jobId,
            String jobTitle,
            String companyName,
            Integer candidateId,
            String candidateName,
            Integer cvDocumentId,
            String cvFileName,
            boolean hasCvFile,
            ApplicationStatus status,
            String coverLetter,
            LocalDateTime appliedAt,
            int rating,
            String internalNote,
            ApplicationCvDto cv,
            ApplicationMatchDto match,
            List<ApplicationHistoryDto> history
    ) {
    }
}
