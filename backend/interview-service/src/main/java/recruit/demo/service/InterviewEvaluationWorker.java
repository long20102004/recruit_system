package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import recruit.demo.repository.InterviewResponseRepository;

@Component
@RequiredArgsConstructor
@Slf4j
public class InterviewEvaluationWorker {
    private final InterviewResponseRepository responses;
    private final InterviewService interviews;

    @Scheduled(fixedDelayString = "${app.interview.evaluation-poll-ms:1000}")
    public void evaluatePendingAnswers() {
        for (var pending : responses.pending(PageRequest.of(0, 8))) {
            try {
                interviews.evaluatePending(pending.getSessionId(), pending.getResponseId());
            } catch (RuntimeException failure) {
                log.warn("Could not evaluate answer {}: {}", pending.getResponseId(), failure.getMessage());
                responses.failPending(pending.getResponseId());
            }
        }
    }
}
