package recruit.demo.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.JobService;

@RestController
@RequestMapping("/api/jobs")
@RequiredArgsConstructor
public class JobsController {

    private final JobService jobService;

    @GetMapping
    public BaseResponse<PageResponse<JobDtos.JobResponse>> list(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) String location,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        String cityOrLocation = city != null ? city : location;
        return BaseResponse.success(jobService.list(keyword, cityOrLocation, status, Paging.of(page, size)));
    }

    @GetMapping("/mine")
    @PreAuthorize("hasAuthority('job:read-own')")
    public BaseResponse<PageResponse<JobDtos.JobResponse>> myJobs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(jobService.myJobs(Paging.of(page, size)));
    }

    @GetMapping("/{id}")
    public JobDtos.JobResponse get(@PathVariable Integer id) {
        return jobService.getById(id);
    }

    @PostMapping
    @PreAuthorize("hasAuthority('job:create')")
    public JobDtos.JobResponse create(@Valid @RequestBody JobDtos.CreateJobRequest request) {
        return jobService.create(request);
    }

    @PatchMapping("/{id}/status")
    @PreAuthorize("hasAuthority('job:update')")
    public JobDtos.JobResponse updateStatus(@PathVariable Integer id,
                                            @Valid @RequestBody JobDtos.UpdateJobStatusRequest request) {
        return jobService.updateStatus(id, request.status());
    }
}
