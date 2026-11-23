package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.DashboardDtos;
import recruit.demo.entity.JobStatus;
import recruit.demo.entity.Role;
import recruit.demo.repository.JobApplicationRepository;
import recruit.demo.repository.JobRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;

@Service
@RequiredArgsConstructor
public class DashboardService {

    private final JobRepository jobRepository;
    private final JobApplicationRepository applicationRepository;
    private final recruit.demo.client.ServiceHttpClient serviceHttp;
    @org.springframework.beans.factory.annotation.Value("${app.services.interview-url}")
    private String interviewUrl;

    @Transactional(readOnly = true)
    public DashboardDtos.RecruiterStatsResponse recruiterStats() {
        SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
        UserPrincipal principal = SecurityUtils.currentUser();

        long openJobs = jobRepository.countByStatusAndCreatedById(JobStatus.PUBLISHED, principal.getId());
        long applications = applicationRepository.countByJobCreatedById(principal.getId());
        long questions = serviceHttp.get(interviewUrl + "/internal/interviews/question-count", recruit.demo.dto.ServiceDtos.QuestionCount.class).count();
        return new DashboardDtos.RecruiterStatsResponse(openJobs, applications, questions);
    }
}
