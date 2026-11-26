package recruit.demo.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ApplicationDtos;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.ApplicationService;

@RestController
@RequestMapping("/api/applications")
@RequiredArgsConstructor
public class ApplicationsController {

    private final ApplicationService applicationService;

    @PostMapping("/jobs/{jobId}")
    @PreAuthorize("hasAuthority('application:apply')")
    public ApplicationDtos.ApplicationResponse apply(@PathVariable Integer jobId,
                                                     @RequestBody(required = false) ApplicationDtos.ApplyRequest request) {
        return applicationService.apply(jobId, request);
    }

    @GetMapping("/mine")
    @PreAuthorize("hasAuthority('application:read-own')")
    public BaseResponse<PageResponse<ApplicationDtos.ApplicationResponse>> myApplications(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(applicationService.myApplications(Paging.of(page, size)));
    }

    @GetMapping("/recruiter")
    @PreAuthorize("hasAuthority('application:read-received')")
    public BaseResponse<PageResponse<ApplicationDtos.ApplicationResponse>> recruiterApplications(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(applicationService.recruiterApplications(Paging.of(page, size)));
    }
}
