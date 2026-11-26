package recruit.demo.dto;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public final class DashboardDtos {

    private DashboardDtos() {
    }

    public record ExpiringJobItem(
            Integer id,
            String title,
            LocalDateTime deadline,
            long applicantsCount
    ) {
    }

    public record RecruiterStatsResponse(
            long openJobsCount,
            long applicationsCount,
            long questionsCount,
            long draftJobsCount,
            long newApplicationsCount,
            long previousPeriodApplicationsCount,
            long pendingApplicationsCount,
            long completedInterviewsCount,
            Double averageInterviewScore,
            Map<String, Long> funnel,
            List<ExpiringJobItem> expiringJobs
    ) {
        public RecruiterStatsResponse(long openJobsCount, long applicationsCount, long questionsCount) {
            this(openJobsCount, applicationsCount, questionsCount, 0L, 0L, 0L, 0L, 0L, null, Map.of(), List.of());
        }
    }
}
