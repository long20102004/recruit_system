package recruit.demo.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import recruit.demo.dto.ServiceDtos.QuestionCount;

/** API nội bộ của interview-service. */
@FeignClient(name = "interview-service", contextId = "interviewServiceClient", url = "${app.services.interview-url}")
public interface InterviewServiceClient {

    @GetMapping("/internal/interviews/question-count")
    QuestionCount questionCount();
}
