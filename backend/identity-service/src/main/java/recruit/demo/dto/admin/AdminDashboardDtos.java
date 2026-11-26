package recruit.demo.dto.admin;

import java.time.LocalDateTime;
import java.util.List;

public final class AdminDashboardDtos {

    private AdminDashboardDtos() {
    }

    public record AdminKpiDto(String id, String label, String value, String note) {
    }

    public record RoleBreakdownDto(String role, String label, long count) {
    }

    public record AdminActivityLogDto(
            Integer id,
            LocalDateTime createdAt,
            String time,
            String event,
            String badgeClass,
            String target,
            String actor
    ) {
    }

    public record AdminDashboardResponse(
            List<AdminKpiDto> kpis,
            List<RoleBreakdownDto> roles,
            long lockedUsersCount,
            List<AdminActivityLogDto> activityLog
    ) {
    }
}
