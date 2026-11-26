package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ServiceDtos.InterviewAdminStats;
import recruit.demo.dto.ServiceDtos.QuestionCount;
import recruit.demo.dto.ServiceDtos.RecruiterInterviewStats;
import recruit.demo.enums.SessionStatus;
import recruit.demo.repository.EvaluationResultRepository;
import recruit.demo.repository.InterviewQuestionRepository;
import recruit.demo.repository.InterviewSessionRepository;

import java.time.LocalDateTime;

@RestController
@RequiredArgsConstructor
public class InternalInterviewController {
    private final InterviewQuestionRepository questions;
    private final InterviewSessionRepository sessions;
    private final EvaluationResultRepository evaluations;

    @GetMapping("/internal/interviews/question-count")
    public QuestionCount count() {
        return new QuestionCount(questions.countByActiveTrue());
    }

    @GetMapping("/internal/interviews/admin-stats")
    public InterviewAdminStats adminStats() {
        long activeQuestions = questions.countByActiveTrue();
        long totalQuestions = questions.count();
        long completedSessions = sessions.countByStatus(SessionStatus.COMPLETED);
        Double avg = evaluations.averageScoreAll();
        return new InterviewAdminStats(totalQuestions, Math.max(0, totalQuestions - activeQuestions), completedSessions, avg);
    }

    @GetMapping("/internal/interviews/recruiter-stats")
    public RecruiterInterviewStats recruiterStats(
            @RequestParam("recruiterUserId") Integer recruiterUserId,
            @RequestParam(value = "days", defaultValue = "30") int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(Math.max(1, days));
        long completed = sessions.countByRecruiterUserIdAndStatusAndCompletedAtAfter(
                recruiterUserId, SessionStatus.COMPLETED, since);
        Double avg = evaluations.averageScoreForRecruiter(recruiterUserId, since);
        return new RecruiterInterviewStats(completed, avg);
    }
}
