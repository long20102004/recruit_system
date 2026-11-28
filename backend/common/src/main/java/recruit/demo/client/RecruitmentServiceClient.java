package recruit.demo.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import recruit.demo.dto.ServiceDtos.InterviewContext;
import recruit.demo.dto.ServiceDtos.RecruitmentAdminStats;

/** API nội bộ của recruitment-service. */
@FeignClient(name = "recruitment-service", contextId = "recruitmentServiceClient", url = "${app.services.recruitment-url}")
public interface RecruitmentServiceClient {

    @GetMapping("/internal/interview-access")
    boolean canReadInterview(@RequestParam("userId") Integer userId, @RequestParam("jobId") Integer jobId);

    @GetMapping("/internal/interview-eligibility")
    boolean interviewEligible(@RequestParam("userId") Integer userId,
                              @RequestParam("applicationId") Integer applicationId);

    @org.springframework.web.bind.annotation.PostMapping("/internal/interview-results")
    void saveInterviewResult(@org.springframework.web.bind.annotation.RequestBody
                             recruit.demo.dto.ServiceDtos.CompletedInterview result);

    /** jobId, applicationId null thì không gửi. */
    @GetMapping("/internal/interview-context")
    InterviewContext interviewContext(@RequestParam("userId") Integer userId,
                                      @RequestParam(value = "jobId", required = false) Integer jobId,
                                      @RequestParam(value = "applicationId", required = false) Integer applicationId);

    @GetMapping("/internal/stats/admin")
    RecruitmentAdminStats adminStats();
}
