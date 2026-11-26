package recruit.demo.service.impl;

import recruit.demo.service.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.DashboardDtos;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.Role;
import recruit.demo.repository.JobApplicationRepository;
import recruit.demo.repository.JobRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;

@Service
@RequiredArgsConstructor
public class DashboardServiceImpl implements DashboardService {

    private final JobRepository jobRepository;
    private final JobApplicationRepository applicationRepository;
    private final recruit.demo.client.InterviewServiceClient interviewClient;

    @Transactional(readOnly = true)
    public DashboardDtos.RecruiterStatsResponse recruiterStats() {
        SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
        UserPrincipal principal = SecurityUtils.currentUser();

        long openJobs = jobRepository.countByStatusAndCreatedById(JobStatus.PUBLISHED, principal.getId());
        long applications = applicationRepository.countByJobCreatedById(principal.getId());
        long questions = interviewClient.questionCount().count();
        return new DashboardDtos.RecruiterStatsResponse(openJobs, applications, questions);
    }
}
