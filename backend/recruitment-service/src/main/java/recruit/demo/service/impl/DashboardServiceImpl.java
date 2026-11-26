package recruit.demo.service.impl;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.DashboardDtos.ExpiringJobItem;
import recruit.demo.dto.DashboardDtos.RecruiterStatsResponse;
import recruit.demo.dto.ServiceDtos.RecruiterInterviewStats;
import recruit.demo.entity.Job;
import recruit.demo.enums.ApplicationStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.repository.JobApplicationRepository;
import recruit.demo.repository.JobRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.DashboardService;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class DashboardServiceImpl implements DashboardService {

    private final JobRepository jobRepository;
    private final JobApplicationRepository applicationRepository;
    private final recruit.demo.client.InterviewServiceClient interviewClient;

    @Override
    @Transactional(readOnly = true)
    public RecruiterStatsResponse recruiterStats() {
        return recruiterStats(30);
    }

    @Override
    @Transactional(readOnly = true)
    public RecruiterStatsResponse recruiterStats(int daysRaw) {
        int days = daysRaw <= 7 ? 7 : 30;
        UserPrincipal principal = SecurityUtils.currentUser();
        Integer userId = principal.getId();

        LocalDateTime now = LocalDateTime.now();
        LocalDateTime start = now.minusDays(days);
        LocalDateTime prevStart = now.minusDays(days * 2L);

        long openJobs = jobRepository.countByStatusAndCreatedById(JobStatus.PUBLISHED, userId);
        long draftJobs = jobRepository.countByStatusAndCreatedById(JobStatus.DRAFT, userId);
        long totalApps = applicationRepository.countByJobCreatedById(userId);
        long newApps = applicationRepository.countByJobCreatedByIdAndAppliedAtBetween(userId, start, now);
        long prevApps = applicationRepository.countByJobCreatedByIdAndAppliedAtBetween(userId, prevStart, start);
        long pendingApps = applicationRepository.countByJobCreatedByIdAndStatus(userId, ApplicationStatus.SUBMITTED);

        long questions = 0L;
        try {
            questions = interviewClient.questionCount().count();
        } catch (Exception ignored) {
        }

        long completedInterviews = 0L;
        Double avgScore = null;
        try {
            RecruiterInterviewStats ivStats = interviewClient.recruiterStats(userId, days);
            if (ivStats != null) {
                completedInterviews = ivStats.completedSessions();
                avgScore = ivStats.averageScore();
            }
        } catch (Exception ignored) {
        }

        Map<String, Long> funnel = new LinkedHashMap<>();
        funnel.put("SUBMITTED", newApps);
        funnel.put("REVIEWING", applicationRepository.countByJobCreatedByIdAndStatusAndAppliedAtBetween(
                userId, ApplicationStatus.REVIEWING, start, now));
        funnel.put("INTERVIEW", applicationRepository.countByJobCreatedByIdAndStatusAndAppliedAtBetween(
                userId, ApplicationStatus.INTERVIEW, start, now));
        funnel.put("HIRED", applicationRepository.countByJobCreatedByIdAndStatusAndAppliedAtBetween(
                userId, ApplicationStatus.HIRED, start, now));
        funnel.put("REJECTED", applicationRepository.countByJobCreatedByIdAndStatusAndAppliedAtBetween(
                userId, ApplicationStatus.REJECTED, start, now));

        List<Job> expiring = jobRepository.findByCreatedByIdAndStatusAndDeadlineBetweenOrderByDeadlineAsc(
                userId, JobStatus.PUBLISHED, now, now.plusDays(7));
        List<ExpiringJobItem> expiringItems = expiring.stream()
                .map(j -> new ExpiringJobItem(
                        j.getId(),
                        j.getTitle(),
                        j.getDeadline(),
                        applicationRepository.countByJobId(j.getId())
                ))
                .toList();

        return new RecruiterStatsResponse(
                openJobs,
                totalApps,
                questions,
                draftJobs,
                newApps,
                prevApps,
                pendingApps,
                completedInterviews,
                avgScore,
                funnel,
                expiringItems
        );
    }
}
