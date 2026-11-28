package recruit.demo.service;

import org.springframework.data.domain.Pageable;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public interface JobService {
    PageResponse<JobDtos.JobResponse> list(String keyword, String city, String status, Pageable pageable);
    PageResponse<JobDtos.JobResponse> list(String keyword, String city, String status, BigDecimal minSalary, Pageable pageable);
    PageResponse<JobDtos.JobResponse> companyJobs(int companyId, Pageable pageable);
    List<JobDtos.JobResponse> similar(Integer id);
    JobDtos.JobResponse getById(Integer id);
    JobDtos.JobResponse getOwn(Integer id);
    PageResponse<JobDtos.ModeratedJob> moderationJobs(Pageable pageable);
    JobDtos.ModeratedJob moderate(Integer id, JobDtos.LockRequest lock);
    JobDtos.JobResponse create(JobDtos.CreateJobRequest request);
    JobDtos.JobResponse update(Integer id, JobDtos.UpdateJobRequest request);
    void delete(Integer id);
    JobDtos.JobResponse updateStatus(Integer id, String statusRaw);
    JobDtos.JobResponse renew(Integer id, LocalDateTime newDeadline);
    PageResponse<JobDtos.JobResponse> myJobs(Pageable pageable);

    PageResponse<JobDtos.JobResponse> adminList(String status, Integer companyId, String keyword, Pageable pageable);
    Map<Integer, JobDtos.JobLockStateDto> adminLockStates();
    JobDtos.JobLockStateDto lockJob(Integer id, String reason, String note);
    void unlockJob(Integer id);
}
