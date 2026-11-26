package recruit.demo.service;

import java.util.List;
import recruit.demo.dto.JobDtos;

public interface JobService {
    List<JobDtos.JobResponse> list(String keyword, String city, String status);
    JobDtos.JobResponse getById(Integer id);
    JobDtos.JobResponse create(JobDtos.CreateJobRequest request);
    JobDtos.JobResponse updateStatus(Integer id, String statusRaw);
    List<JobDtos.JobResponse> myJobs();
}
