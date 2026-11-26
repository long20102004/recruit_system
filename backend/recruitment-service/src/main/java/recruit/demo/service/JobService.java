package recruit.demo.service;

import java.util.List;
import org.springframework.data.domain.Pageable;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;

public interface JobService {
    PageResponse<JobDtos.JobResponse> list(String keyword, String city, String status, Pageable pageable);
    JobDtos.JobResponse getById(Integer id);
    JobDtos.JobResponse create(JobDtos.CreateJobRequest request);
    JobDtos.JobResponse updateStatus(Integer id, String statusRaw);
    PageResponse<JobDtos.JobResponse> myJobs(Pageable pageable);
}
