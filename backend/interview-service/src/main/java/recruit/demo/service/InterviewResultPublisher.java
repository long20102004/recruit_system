package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import recruit.demo.client.RecruitmentServiceClient;
import recruit.demo.dto.ServiceDtos.CompletedInterview;
import recruit.demo.repository.InterviewSessionRepository;

import java.time.LocalDateTime;

@Component
@RequiredArgsConstructor
@Slf4j
public class InterviewResultPublisher {
    private final InterviewSessionRepository sessions;
    private final RecruitmentServiceClient recruitment;

    @Scheduled(fixedDelayString = "${app.interview.result-export-delay-ms:5000}")
    public void exportCompletedResults() {
        for (var session : sessions.findTop50ByCompletionScoreIsNotNullAndResultExportedAtIsNullOrderByIdAsc()) {
            try {
                recruitment.saveInterviewResult(new CompletedInterview(session.getApplicationId(), session.getJobId(),
                        session.getCandidateUserId(), session.getId(), session.getCompletedAt(), session.getCompletionScore()));
                sessions.markResultExported(session.getId(), LocalDateTime.now());
            } catch (RuntimeException failure) {
                log.warn("Could not export interview result for session {}: {}", session.getId(), failure.getMessage());
            }
        }
    }
}
