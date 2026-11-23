package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.JobDtos;
import recruit.demo.service.JobService;

import java.util.List;

@RestController
@RequestMapping("/api/jobs")
@RequiredArgsConstructor
public class JobsController {

    private final JobService jobService;

    @GetMapping
    public List<JobDtos.JobResponse> list(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) String location,
            @RequestParam(required = false) String status
    ) {
        String cityOrLocation = city != null ? city : location;
        return jobService.list(keyword, cityOrLocation, status);
    }

    @GetMapping("/mine")
    public List<JobDtos.JobResponse> myJobs() {
        return jobService.myJobs();
    }

    @GetMapping("/{id}")
    public JobDtos.JobResponse get(@PathVariable Integer id) {
        return jobService.getById(id);
    }

    @PostMapping
    public JobDtos.JobResponse create(@Valid @RequestBody JobDtos.CreateJobRequest request) {
        return jobService.create(request);
    }

    @PatchMapping("/{id}/status")
    public JobDtos.JobResponse updateStatus(@PathVariable Integer id,
                                            @Valid @RequestBody JobDtos.UpdateJobStatusRequest request) {
        return jobService.updateStatus(id, request.status());
    }
}
