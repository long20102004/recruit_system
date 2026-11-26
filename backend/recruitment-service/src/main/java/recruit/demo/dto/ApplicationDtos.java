package recruit.demo.dto;

import recruit.demo.enums.ApplicationStatus;

import java.time.LocalDateTime;

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
            LocalDateTime appliedAt
    ) {
    }
}
