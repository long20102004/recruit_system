package recruit.demo.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import recruit.demo.dto.ServiceDtos.InterviewContext;

/** API nội bộ của recruitment-service. */
@FeignClient(name = "recruitment-service", contextId = "recruitmentServiceClient", url = "${app.services.recruitment-url}")
public interface RecruitmentServiceClient {

    /** jobId, applicationId null thì không gửi. */
    @GetMapping("/internal/interview-context")
    InterviewContext interviewContext(@RequestParam("userId") Integer userId,
                                      @RequestParam(value = "jobId", required = false) Integer jobId,
                                      @RequestParam(value = "applicationId", required = false) Integer applicationId);
}
