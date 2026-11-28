package recruit.demo.service;

import java.util.List;
import org.springframework.data.domain.Pageable;
import recruit.demo.dto.InterviewDtos;
import recruit.demo.dto.PageResponse;

public interface InterviewService {
    recruit.demo.dto.ServiceDtos.InterviewResult latestResult(Integer applicationId, Integer jobId, Integer candidateUserId);

    PageResponse<InterviewDtos.QuestionResponse> listQuestions(Pageable pageable);
    InterviewDtos.SessionResponse createSession(InterviewDtos.CreateSessionRequest request);
    InterviewDtos.SessionResponse getSession(Integer id);
    InterviewDtos.QueuedEvaluation queueEvaluation(Integer sessionId, InterviewDtos.SubmitResponseRequest request);
    InterviewDtos.QueuedEvaluation evaluationStatus(Integer sessionId, Integer questionId);
    void evaluatePending(Integer sessionId, Integer responseId);
    InterviewDtos.EvaluationResponse submitAndEvaluate(Integer sessionId, InterviewDtos.SubmitResponseRequest request);
    PageResponse<InterviewDtos.SessionResponse> mySessions(Pageable pageable);
    InterviewDtos.SessionSummary summary(Integer id);
}
