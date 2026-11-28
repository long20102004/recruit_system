package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.CompanyDtos.CompanyDto;
import recruit.demo.dto.CompanyDtos.FollowResponse;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.CompanyService;
import recruit.demo.service.JobService;

import java.util.List;

@RestController
@RequestMapping("/api/companies")
@RequiredArgsConstructor
public class CompanyController {

    private final CompanyService companyService;
    private final JobService jobService;

    @GetMapping
    public BaseResponse<List<CompanyDto>> list(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) String industry,
            @RequestParam(required = false, defaultValue = "jobs") String sort
    ) {
        return BaseResponse.success(companyService.listPublic(q, city, industry, sort));
    }

    @GetMapping("/{id}")
    public BaseResponse<CompanyDto> get(@PathVariable Integer id) {
        return BaseResponse.success(companyService.getPublic(id));
    }

    @GetMapping("/{id}/jobs")
    public BaseResponse<PageResponse<JobDtos.JobResponse>> jobs(
            @PathVariable Integer id,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        Pageable pageable = Paging.of(page, size);
        return BaseResponse.success(jobService.companyJobs(id, pageable));
    }

    @PostMapping("/{id}/follow")
    public BaseResponse<FollowResponse> follow(@PathVariable Integer id) {
        return BaseResponse.success(companyService.follow(id));
    }

    @DeleteMapping("/{id}/follow")
    public BaseResponse<FollowResponse> unfollow(@PathVariable Integer id) {
        return BaseResponse.success(companyService.unfollow(id));
    }
}
