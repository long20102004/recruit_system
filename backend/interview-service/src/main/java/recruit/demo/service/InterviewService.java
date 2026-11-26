package recruit.demo.service;

import recruit.demo.enums.Role;
import recruit.demo.enums.SessionStatus;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.AiScoringDtos;
import recruit.demo.dto.InterviewDtos;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class InterviewService {

    private final InterviewQuestionRepository questionRepository;
    private final EvaluationRubricRepository rubricRepository;
    private final InterviewSessionRepository sessionRepository;
    private final InterviewSessionQuestionRepository sessionQuestionRepository;
    private final InterviewResponseRepository responseRepository;
    private final EvaluationResultRepository evaluationResultRepository;
    private final AiScoringClient aiScoringClient;
    private final QuestionSelectionService questionSelection;
    private final recruit.demo.client.RecruitmentServiceClient recruitmentClient;

    @Transactional(readOnly = true)
    public List<InterviewDtos.QuestionResponse> listQuestions() {
        return questionRepository.findByActiveTrueOrderByIdAsc().stream()
                .map(this::toQuestionResponse)
                .toList();
    }

    @Transactional
    public InterviewDtos.SessionResponse createSession(InterviewDtos.CreateSessionRequest request) {
        SecurityUtils.requireRole(Role.CANDIDATE);
        UserPrincipal principal = SecurityUtils.currentUser();
        var context = recruitmentClient.interviewContext(principal.getId(),
                request != null ? request.jobId() : null, request != null ? request.applicationId() : null);

        int count = request != null && request.questionCount() != null ? request.questionCount() : 6;
        if (count < 1 || count > 12) throw new ApiException(HttpStatus.BAD_REQUEST, "Question count must be 1-12");
        List<InterviewQuestion> questions;
        if (request != null && request.questionIds() != null && !request.questionIds().isEmpty()) {
            var ids = request.questionIds();
            if (ids.size() > 12 || new HashSet<>(ids).size() != ids.size() || ids.stream().anyMatch(Objects::isNull))
                throw new ApiException(HttpStatus.BAD_REQUEST, "Question IDs must be distinct, non-null and at most 12");
            var found = questionRepository.findAllById(ids);
            if (found.size() != ids.size() || found.stream().anyMatch(q -> !q.isActive()))
                throw new ApiException(HttpStatus.BAD_REQUEST, "Question is missing or inactive");
            var byId = found.stream().collect(Collectors.toMap(InterviewQuestion::getId, q -> q));
            questions = ids.stream().map(byId::get).toList();
        } else {
            var recent = new HashSet<>(sessionQuestionRepository.recentQuestionIds(principal.getId(),
                org.springframework.data.domain.PageRequest.of(0, 36)));
            questions = questionSelection.select(questionRepository.findByActiveTrueOrderByIdAsc(), context, recent, count);
        }
        if (questions.isEmpty()) throw new ApiException(HttpStatus.BAD_REQUEST, "No interview questions available");

        String title = context.jobId() != null ? "Interview – " + context.jobTitle() : "Practice Interview";
        InterviewSession session = InterviewSession.builder()
                .candidateId(context.candidateId())
                .candidateUserId(principal.getId())
                .recruiterUserId(context.recruiterUserId())
                .jobId(context.jobId())
                .jobTitle(context.jobTitle())
                .applicationId(context.applicationId())
                .title(title)
                .status(SessionStatus.CREATED)
                .build();
        sessionRepository.save(session);

        int order = 1;
        for (InterviewQuestion q : questions) {
            sessionQuestionRepository.save(InterviewSessionQuestion.builder()
                    .session(session)
                    .question(q)
                    .questionOrder(order++)
                    .maxScore(q.getMaxScore() != null ? q.getMaxScore() : new BigDecimal("10.0"))
                    .build());
        }
        return toSessionResponse(session);
    }

    @Transactional(readOnly = true)
    public InterviewDtos.SessionResponse getSession(Integer id) {
        InterviewSession session = sessionRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Session not found"));
        ensureCanAccess(session);
        return toSessionResponse(session);
    }

    @Transactional
    public InterviewDtos.EvaluationResponse submitAndEvaluate(Integer sessionId, InterviewDtos.SubmitResponseRequest request) {
        SecurityUtils.requireRole(Role.CANDIDATE);
        InterviewSession session = sessionRepository.findForUpdate(sessionId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Session not found"));
        ensureCanAccess(session);
        if (session.getStatus() == SessionStatus.COMPLETED)
            throw new ApiException(HttpStatus.CONFLICT, "Session completed; start another practice session");
        InterviewSessionQuestion sessionQuestion = sessionQuestionRepository
            .findBySessionIdAndQuestionId(sessionId, request.questionId())
            .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Question not in session"));
        InterviewQuestion question = sessionQuestion.getQuestion();
        if (session.getStartedAt() == null) session.setStartedAt(LocalDateTime.now());
        session.setStatus(SessionStatus.IN_PROGRESS);
        InterviewResponse response = responseRepository.findBySessionQuestionId(sessionQuestion.getId())
            .orElse(InterviewResponse.builder().sessionQuestion(sessionQuestion).build());
        response.setAnswerText(request.answerText()); response.setStatus("SUBMITTED");
        responseRepository.save(response);
        EvaluationResult evaluation = evaluate(response, question, sessionQuestion);
        if (evaluations(session).size() == sessionQuestionRepository.findBySessionIdOrdered(sessionId).size()) {
            session.setStatus(SessionStatus.COMPLETED); session.setCompletedAt(LocalDateTime.now());
        }
        sessionRepository.save(session);
        return toEvaluationResponse(evaluation, question.getId());
    }

    @Transactional(readOnly=true)
    public List<InterviewDtos.SessionResponse> mySessions() {
        SecurityUtils.requireRole(Role.CANDIDATE);
        return sessionRepository.findByCandidateUserIdOrderByCreatedAtDesc(SecurityUtils.currentUser().getId())
            .stream().map(this::toSessionResponse).toList();
    }

    @Transactional(readOnly=true)
    public InterviewDtos.SessionSummary summary(Integer id) {
        var session = sessionRepository.findById(id)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Session not found"));
        ensureCanAccess(session);
        var results = evaluations(session);
        BigDecimal average = results.isEmpty() ? null : results.stream().map(InterviewDtos.EvaluationResponse::predictedScore)
            .reduce(BigDecimal.ZERO, BigDecimal::add).divide(BigDecimal.valueOf(results.size()),2,RoundingMode.HALF_UP);
        return new InterviewDtos.SessionSummary(id,session.getStatus(),
            sessionQuestionRepository.findBySessionIdOrdered(id).size(),results.size(),average,results);
    }

    private List<InterviewDtos.EvaluationResponse> evaluations(InterviewSession session) {
        List<InterviewDtos.EvaluationResponse> result = new ArrayList<>();
        for (var item : sessionQuestionRepository.findBySessionIdOrdered(session.getId())) {
            responseRepository.findBySessionQuestionId(item.getId()).flatMap(r -> evaluationResultRepository.findByResponseId(r.getId()))
                .ifPresent(e -> result.add(toEvaluationResponse(e,item.getQuestion().getId())));
        }
        return result;
    }

    private EvaluationResult evaluate(InterviewResponse response, InterviewQuestion question,
                                      InterviewSessionQuestion sessionQuestion) {
        BigDecimal maxScore = sessionQuestion.getMaxScore() != null
                ? sessionQuestion.getMaxScore()
                : (question.getMaxScore() != null ? question.getMaxScore() : new BigDecimal("10.0"));

        List<EvaluationRubric> rubrics = rubricRepository.findByQuestionId(question.getId());
        List<AiScoringDtos.CriterionIn> criteria = toAiCriteria(rubrics, question);

        // Always score via AI API (no rule-based / sample-data fallback)
        AiScoringDtos.EvaluateResult aiResult = aiScoringClient.evaluate(
                response.getAnswerText(),
                question.getQuestionText(),
                question.getReferenceAnswer(),
                criteria,
                "db-" + question.getId()
        );
        return saveAiEvaluation(response, aiResult, maxScore);
    }

    private EvaluationResult saveAiEvaluation(
            InterviewResponse response,
            AiScoringDtos.EvaluateResult ai,
            BigDecimal maxScore
    ) {
        BigDecimal score = BigDecimal.valueOf(ai.predictedScore())
                .min(maxScore)
                .max(BigDecimal.ZERO)
                .setScale(2, RoundingMode.HALF_UP);

        EvaluationResult result = evaluationResultRepository.findByResponseId(response.getId())
                .orElse(EvaluationResult.builder().response(response).build());
        result.setPredictedScore(score);
        result.setCompletenessScore(BigDecimal.valueOf(ai.coverageScore() * 10).setScale(2,RoundingMode.HALF_UP));
        // Similarity is not a truth/technical-correctness probability.
        result.setCorrectnessScore(null);
        result.setStrengths(ai.coveredPoints() != null ? List.copyOf(ai.coveredPoints()) : List.of());
        result.setMissingPoints(ai.missingPoints() != null ? List.copyOf(ai.missingPoints()) : List.of());
        result.setFeedback(ai.comment());
        result.setEvaluationMethod(evaluationMethod(ai.mode()));
        result.setScoringMode(ai.mode());
        result.setScoringModelVersion(ai.modelVersion());
        result.setCoverageScore(BigDecimal.valueOf(ai.coverageScore()).setScale(4,RoundingMode.HALF_UP));
        result.setCriterionResults(ai.criterionResults());
        result.setModelVersion(null);
        result.setBertscorePrecision(decimal(ai.bertscorePrecision()));
        result.setBertscoreRecall(decimal(ai.bertscoreRecall()));
        result.setBertscoreF1(decimal(ai.bertscoreF1()));
        return evaluationResultRepository.save(result);
    }

    private BigDecimal decimal(Double value) {
        return value == null ? null : BigDecimal.valueOf(value).setScale(4,RoundingMode.HALF_UP);
    }

    private static String evaluationMethod(String mode) {
        if ("bertscore".equals(mode)) return "BERTSCORE_RUBRIC";
        if ("finetune".equals(mode)) return "FINETUNE_RUBRIC";
        return "FAST_RUBRIC";
    }

    private List<AiScoringDtos.CriterionIn> toAiCriteria(List<EvaluationRubric> rubrics, InterviewQuestion question) {
        if (rubrics == null || rubrics.isEmpty())
            throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, "Question has no scoring rubric");
        return rubrics.stream().map(r -> new AiScoringDtos.CriterionIn("c" + r.getId(),r.getCriterionName(),
            r.getWeight() == null ? 1 : r.getWeight().doubleValue(),
            Optional.ofNullable(r.getExpectedKeywords()).orElse(List.of()),
            r.getReferenceAnswers() == null || r.getReferenceAnswers().isEmpty()
                ? List.of(Objects.toString(r.getCriterionDescription(), r.getCriterionName())) : r.getReferenceAnswers(),
            Optional.ofNullable(r.getMisconceptions()).orElse(List.of()))).toList();
    }

    private InterviewDtos.QuestionResponse toQuestionResponse(InterviewQuestion q) {
        List<EvaluationRubric> rubrics = rubricRepository.findByQuestionId(q.getId());
        List<String> labels = rubrics.stream().map(EvaluationRubric::getCriterionName).toList();
        return new InterviewDtos.QuestionResponse(
                q.getId(),
                q.getTopic(),
                q.getDifficulty(),
                q.getSkill(),
                q.getQuestionText(),
                null,
                labels
        );
    }

    private InterviewDtos.SessionResponse toSessionResponse(InterviewSession session) {
        List<InterviewSessionQuestion> sessionQuestions = sessionQuestionRepository.findBySessionIdOrdered(session.getId());
        List<InterviewDtos.SessionQuestionItem> items = sessionQuestions.stream()
                .map(sq -> new InterviewDtos.SessionQuestionItem(
                        sq.getQuestion().getId(),
                        sq.getQuestionOrder(),
                        sq.getQuestion().getTopic(),
                        sq.getQuestion().getDifficulty(),
                        sq.getQuestion().getQuestionText()
                ))
                .toList();
        Set<Integer> graded = evaluations(session).stream().map(InterviewDtos.EvaluationResponse::questionId).collect(Collectors.toSet());
        int currentIndex = 0;
        while (currentIndex < items.size() && graded.contains(items.get(currentIndex).questionId())) currentIndex++;
        return new InterviewDtos.SessionResponse(
                session.getId(),
                session.getStatus(),
                currentIndex,
                session.getJobId(),
                session.getJobTitle() != null ? session.getJobTitle() : session.getTitle(),
                items,
                session.getCreatedAt()
        );
    }

    private InterviewDtos.EvaluationResponse toEvaluationResponse(EvaluationResult e, Integer questionId) {
        String modelVersion = e.getScoringModelVersion() != null ? e.getScoringModelVersion() :
            e.getModelVersion() == null ? e.getEvaluationMethod() : e.getModelVersion().getModelName()+"-"+e.getModelVersion().getVersion();
        return new InterviewDtos.EvaluationResponse(
                e.getResponse().getId(),
                questionId,
                e.getPredictedScore(),
                "0-10",
                e.getStrengths() != null ? e.getStrengths() : List.of(),
                e.getMissingPoints() != null ? e.getMissingPoints() : List.of(),
                e.getFeedback(),
                e.getEvaluationMethod(),
                modelVersion,
                e.getScoringMode(), e.getBertscorePrecision(), e.getBertscoreRecall(), e.getBertscoreF1(),
                e.getCoverageScore(), e.getCriterionResults() == null ? List.of() : e.getCriterionResults()
        );
    }

    private void ensureCanAccess(InterviewSession session) {
        UserPrincipal principal = SecurityUtils.currentUser();
        if (principal.getRole() == Role.ADMIN ||
            (principal.getRole() == Role.RECRUITER && principal.getId().equals(session.getRecruiterUserId()))) {
            return;
        }
        if (!session.getCandidateUserId().equals(principal.getId())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Not your interview session");
        }
    }
}
