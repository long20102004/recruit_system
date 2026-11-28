package recruit.demo.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import recruit.demo.dto.ServiceDtos.InterviewAdminStats;
import recruit.demo.dto.ServiceDtos.QuestionCount;
import recruit.demo.dto.ServiceDtos.RecruiterInterviewStats;

/** API nội bộ của interview-service. */
@FeignClient(name = "interview-service", contextId = "interviewServiceClient", url = "${app.services.interview-url}")
public interface InterviewServiceClient {

    @GetMapping("/internal/interviews/latest-result")
    recruit.demo.dto.ServiceDtos.InterviewResult latestResult(
            @org.springframework.web.bind.annotation.RequestParam("applicationId") Integer applicationId,
            @org.springframework.web.bind.annotation.RequestParam("jobId") Integer jobId,
            @org.springframework.web.bind.annotation.RequestParam("candidateUserId") Integer candidateUserId);

    @GetMapping("/internal/interviews/question-count")
    QuestionCount questionCount();

    @GetMapping("/internal/interviews/admin-stats")
    InterviewAdminStats adminStats();

    @GetMapping("/internal/interviews/recruiter-stats")
    RecruiterInterviewStats recruiterStats(@RequestParam("recruiterUserId") Integer recruiterUserId,
                                           @RequestParam(value = "days", defaultValue = "30") int days);
}
