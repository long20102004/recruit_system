package recruit.demo.dto;

import java.util.List;

/** Result from HireLens AI {@code POST /v1/interview/evaluate}. */
public final class AiScoringDtos {

    private AiScoringDtos() {
    }

    public record CriterionIn(
            String key,
            String label,
            double weight,
            List<String> hints,
            List<String> referenceAnswers,
            List<String> misconceptions
    ) {
    }

    public record EvaluateResult(
            double predictedScore,
            String scoreScale,
            List<String> coveredPoints,
            List<String> missingPoints,
            String comment,
            String modelVersion,
            String mode,
            Double bertscorePrecision,
            Double bertscoreRecall,
            Double bertscoreF1,
            double coverageScore,
            java.util.List<java.util.Map<String,Object>> criterionResults
    ) {
    }
}
