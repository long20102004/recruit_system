package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.JobService;

import java.util.Map;

@RestController
@RequestMapping("/api/admin/jobs")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN') or hasAuthority('job:moderate')")
public class AdminJobController {

    private final JobService jobService;

    @GetMapping
    public BaseResponse<PageResponse<JobDtos.JobResponse>> list(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Integer companyId,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "100") int size
    ) {
        return BaseResponse.success(jobService.adminList(status, companyId, keyword, Paging.of(page, size)));
    }

    @GetMapping("/locks")
    public BaseResponse<Map<Integer, JobDtos.JobLockStateDto>> lockStates() {
        return BaseResponse.success(jobService.adminLockStates());
    }

    @PostMapping("/{id}/lock")
    public BaseResponse<JobDtos.JobLockStateDto> lock(@PathVariable Integer id,
                                                      @Valid @RequestBody JobDtos.AdminLockJobRequest request) {
        return BaseResponse.success(jobService.lockJob(id, request.reason(), request.note()));
    }

    @PostMapping("/{id}/unlock")
    public BaseResponse<Void> unlock(@PathVariable Integer id) {
        jobService.unlockJob(id);
        return BaseResponse.success(null);
    }
}
