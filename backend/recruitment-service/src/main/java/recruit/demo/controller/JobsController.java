package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.JobService;

import java.math.BigDecimal;

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
            @RequestParam(required = false) BigDecimal minSalary,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        String cityOrLocation = city != null ? city : location;
        return BaseResponse.success(jobService.list(keyword, cityOrLocation, status, minSalary, Paging.of(page, size)));
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

    @PutMapping("/{id}")
    @PreAuthorize("hasAuthority('job:update')")
    public JobDtos.JobResponse update(@PathVariable Integer id,
                                      @Valid @RequestBody JobDtos.UpdateJobRequest request) {
        return jobService.update(id, request);
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasAuthority('job:update')")
    public ResponseEntity<Void> delete(@PathVariable Integer id) {
        jobService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @PatchMapping("/{id}/status")
    @PreAuthorize("hasAuthority('job:update')")
    public JobDtos.JobResponse updateStatus(@PathVariable Integer id,
                                            @Valid @RequestBody JobDtos.UpdateJobStatusRequest request) {
        return jobService.updateStatus(id, request.status());
    }

    @PostMapping("/{id}/renew")
    @PreAuthorize("hasAuthority('job:update')")
    public JobDtos.JobResponse renew(@PathVariable Integer id,
                                     @RequestBody(required = false) JobDtos.RenewJobRequest request) {
        return jobService.renew(id, request != null ? request.deadline() : null);
    }
}
