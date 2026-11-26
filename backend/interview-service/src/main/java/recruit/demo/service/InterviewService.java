package recruit.demo.service;

import java.util.List;
import recruit.demo.dto.InterviewDtos;

public interface InterviewService {
    List<InterviewDtos.QuestionResponse> listQuestions();
    InterviewDtos.SessionResponse createSession(InterviewDtos.CreateSessionRequest request);
    InterviewDtos.SessionResponse getSession(Integer id);
    InterviewDtos.EvaluationResponse submitAndEvaluate(Integer sessionId, InterviewDtos.SubmitResponseRequest request);
    List<InterviewDtos.SessionResponse> mySessions();
    InterviewDtos.SessionSummary summary(Integer id);
}
