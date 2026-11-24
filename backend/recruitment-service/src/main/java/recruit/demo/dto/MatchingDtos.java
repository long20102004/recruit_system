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
            LocalDateTime createdAt,
            /** cvmatch: high | mid | low (null voi engine legacy). */
            String band,
            /** diem bi chan tran vi thieu ky nang bat buoc (cvmatch). */
            Boolean capApplied,
            String engine,
            boolean hasExplanation,
            List<String> partialSkills
    ) {
    }

    /** Giai thich cua mot ket qua cvmatch (lay luoi, luu lai). */
    public record ExplanationResponse(
            Integer matchId,
            String audience,
            String band,
            String bandLabel,
            Integer score,
            Boolean capApplied,
            String text,
            Object sections
    ) {
    }

    public record RefreshJobRequest(String scope) {
    }

    public record RunMatchingRequest(Integer jobId, Integer candidateId) {
    }
}
