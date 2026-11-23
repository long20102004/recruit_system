package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ApplicationDtos;
import recruit.demo.service.ApplicationService;

import java.util.List;

@RestController
@RequestMapping("/api/applications")
@RequiredArgsConstructor
public class ApplicationsController {

    private final ApplicationService applicationService;

    @PostMapping("/jobs/{jobId}")
    public ApplicationDtos.ApplicationResponse apply(@PathVariable Integer jobId,
                                                     @RequestBody(required = false) ApplicationDtos.ApplyRequest request) {
        return applicationService.apply(jobId, request);
    }

    @GetMapping("/mine")
    public List<ApplicationDtos.ApplicationResponse> myApplications() {
        return applicationService.myApplications();
    }

    @GetMapping("/recruiter")
    public List<ApplicationDtos.ApplicationResponse> recruiterApplications() {
        return applicationService.recruiterApplications();
    }
}
