package recruit.demo.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public final class MatchingDtos {

    private MatchingDtos() {
    }

    public record MatchResponse(
            Integer id,
            Integer jobId,
            String jobTitle,
            String companyName,
            Integer candidateId,
            String candidateName,
            BigDecimal overallScore,
            BigDecimal semanticSimilarity,
            BigDecimal tfidfSimilarity,
            BigDecimal skillOverlap,
            List<String> matchedSkills,
            List<String> missingSkills,
            List<String> reasons,
            String modelVersion,
            Integer rankPosition,
            LocalDateTime createdAt
    ) {
    }

    public record RunMatchingRequest(Integer jobId, Integer candidateId) {
    }
}
