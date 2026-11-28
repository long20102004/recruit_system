package recruit.demo.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import recruit.demo.enums.SessionStatus;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public final class InterviewDtos {

    private InterviewDtos() {
    }

    public record QuestionResponse(
            Integer id,
            String topic,
            String difficulty,
            String skill,
            String questionText,
            String referenceAnswer,
            List<String> rubricLabels
    ) {
    }

    public record CreateSessionRequest(Integer jobId, Integer applicationId, List<Integer> questionIds, Integer questionCount) {
    }

    public record SessionQuestionItem(
            Integer questionId,
            int sortOrder,
            String topic,
            String difficulty,
            String questionText
    ) {
    }

    public record SessionResponse(
            Integer id,
            SessionStatus status,
            int currentIndex,
            Integer jobId,
            String jobTitle,
            List<SessionQuestionItem> questions,
            LocalDateTime createdAt
    ) {
    }

    public record SessionSummary(Integer sessionId, SessionStatus status, int totalQuestions,
        int answeredQuestions, BigDecimal averageScore, List<EvaluationResponse> evaluations) {}

    public record QueuedEvaluation(String status, EvaluationResponse evaluation) {}

    public record SubmitResponseRequest(
            @NotNull Integer questionId,
            @NotBlank @jakarta.validation.constraints.Size(max=4000) String answerText
    ) {
    }

    public record EvaluationResponse(
            Integer responseId,
            Integer questionId,
            BigDecimal predictedScore,
            String scoreScale,
            List<String> coveredPoints,
            List<String> missingPoints,
            String comment,
            String evaluationMethod,
            String modelVersion,
            String scoringMode,
            BigDecimal bertscorePrecision,
            BigDecimal bertscoreRecall,
            BigDecimal bertscoreF1,
            BigDecimal coverageScore,
            List<java.util.Map<String,Object>> criterionResults
    ) {
    }
}
