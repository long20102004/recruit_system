package recruit.demo.service.impl;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.client.InterviewServiceClient;
import recruit.demo.client.RecruitmentServiceClient;
import recruit.demo.dto.ServiceDtos.AuditLogCreateRequest;
import recruit.demo.dto.ServiceDtos.InterviewAdminStats;
import recruit.demo.dto.ServiceDtos.RecruitmentAdminStats;
import recruit.demo.dto.admin.AdminDashboardDtos.*;
import recruit.demo.entity.AuditLog;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.repository.AuditLogRepository;
import recruit.demo.repository.UserRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.service.AdminDashboardService;

import java.text.NumberFormat;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;

@Service
@RequiredArgsConstructor
public class AdminDashboardServiceImpl implements AdminDashboardService {

    private static final DateTimeFormatter SHORT_FMT = DateTimeFormatter.ofPattern("dd/MM HH:mm");

    private final UserRepository users;
    private final AuditLogRepository auditLogs;
    private final RecruitmentServiceClient recruitmentClient;
    private final InterviewServiceClient interviewClient;

    @Override
    @Transactional(readOnly = true)
    public AdminDashboardResponse getDashboard() {
        long totalUsers = users.count();
        long newUsers30d = users.countByCreatedAtAfter(LocalDateTime.now().minusDays(30));
        long candidates = users.countByRole(Role.CANDIDATE);
        long recruiters = users.countByRole(Role.RECRUITER);
        long admins = users.countByRole(Role.ADMIN);
        long lockedUsers = users.countByStatus(UserStatus.BANNED);

        RecruitmentAdminStats recStats = safeRecruitmentStats();
        InterviewAdminStats ivStats = safeInterviewStats();

        String appDeltaNote = formatDeltaNote(recStats.applicationsLast30Days(), recStats.applicationsPrev30Days());

        List<AdminKpiDto> kpis = List.of(
                new AdminKpiDto("users", "Người dùng", fmt(totalUsers), "+" + fmt(newUsers30d) + " trong 30 ngày"),
                new AdminKpiDto("companies", "Công ty hoạt động", fmt(recStats.activeCompanies()),
                        fmt(recStats.pendingCompanies()) + " chờ duyệt"),
                new AdminKpiDto("jobs", "Tin đang đăng", fmt(recStats.publishedJobs()),
                        fmt(recStats.lockedJobs()) + " tin bị khoá"),
                new AdminKpiDto("applications", "Đơn ứng tuyển (30 ngày)", fmt(recStats.applicationsLast30Days()),
                        appDeltaNote),
                new AdminKpiDto("questions", "Câu hỏi phỏng vấn", fmt(ivStats.totalQuestions()),
                        fmt(ivStats.pendingApprovalQuestions()) + " cần chuyên gia duyệt")
        );

        List<RoleBreakdownDto> roles = List.of(
                new RoleBreakdownDto("CANDIDATE", "Ứng viên", candidates),
                new RoleBreakdownDto("RECRUITER", "Nhà tuyển dụng", recruiters),
                new RoleBreakdownDto("ADMIN", "Admin", admins)
        );

        List<AdminActivityLogDto> logs = auditLogs.findTop20ByOrderByCreatedAtDescIdDesc()
                .stream()
                .map(AdminDashboardServiceImpl::toDto)
                .toList();

        return new AdminDashboardResponse(kpis, roles, lockedUsers, logs);
    }

    @Override
    @Transactional
    public AdminActivityLogDto recordAuditLog(AuditLogCreateRequest request) {
        String actorEmail = request.actorEmail();
        Integer actorId = request.actorUserId();
        if (actorEmail == null || actorEmail.isBlank()) {
            try {
                var actor = SecurityUtils.currentUser();
                actorEmail = actor.getEmail();
                if (actorId == null) actorId = actor.getId();
            } catch (Exception ex) {
                actorEmail = "admin@hirelens.local";
            }
        }
        AuditLog saved = auditLogs.save(AuditLog.builder()
                .eventType(request.eventType() != null && !request.eventType().isBlank() ? request.eventType() : "ADMIN_ACTION")
                .eventLabel(request.eventLabel() != null && !request.eventLabel().isBlank() ? request.eventLabel() : "Thao tác quản trị")
                .badgeClass(request.badgeClass() != null && !request.badgeClass().isBlank() ? request.badgeClass() : "badge b-brand")
                .target(request.target() != null ? request.target() : "-")
                .actorUserId(actorId)
                .actorEmail(actorEmail)
                .build());
        return toDto(saved);
    }

    private RecruitmentAdminStats safeRecruitmentStats() {
        try {
            RecruitmentAdminStats stats = recruitmentClient.adminStats();
            if (stats != null) return stats;
        } catch (Exception ignored) {
        }
        return new RecruitmentAdminStats(0, 0, 0, 0, 0, 0);
    }

    private InterviewAdminStats safeInterviewStats() {
        try {
            InterviewAdminStats stats = interviewClient.adminStats();
            if (stats != null) return stats;
        } catch (Exception ignored) {
        }
        return new InterviewAdminStats(0, 0, 0, null);
    }

    private String fmt(long v) {
        return NumberFormat.getIntegerInstance(Locale.forLanguageTag("vi-VN")).format(v);
    }

    private String formatDeltaNote(long current, long previous) {
        if (previous <= 0) {
            return current > 0 ? "+" + fmt(current) + " trong kỳ" : "Chưa có dữ liệu kỳ trước";
        }
        long pct = Math.round(((current - previous) * 100.0) / previous);
        return (pct >= 0 ? "+" : "") + pct + "% so với kỳ trước";
    }

    static AdminActivityLogDto toDto(AuditLog log) {
        String time = log.getCreatedAt() != null ? log.getCreatedAt().format(SHORT_FMT) : "";
        return new AdminActivityLogDto(
                log.getId(),
                log.getCreatedAt(),
                time,
                log.getEventLabel(),
                log.getBadgeClass(),
                log.getTarget(),
                log.getActorEmail()
        );
    }
}
