package recruit.demo.dto;

public final class DashboardDtos {

    private DashboardDtos() {
    }

    public record RecruiterStatsResponse(
            long openJobsCount,
            long applicationsCount,
            long questionsCount
    ) {
    }
}
