package recruit.demo.service.impl;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import recruit.demo.client.InterviewServiceClient;
import recruit.demo.client.RecruitmentServiceClient;
import recruit.demo.dto.ServiceDtos.AuditLogCreateRequest;
import recruit.demo.dto.ServiceDtos.InterviewAdminStats;
import recruit.demo.dto.ServiceDtos.RecruitmentAdminStats;
import recruit.demo.entity.AuditLog;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.repository.AuditLogRepository;
import recruit.demo.repository.UserRepository;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class AdminDashboardServiceImplTest {

    private UserRepository users;
    private AuditLogRepository auditLogs;
    private RecruitmentServiceClient recruitmentClient;
    private InterviewServiceClient interviewClient;
    private AdminDashboardServiceImpl service;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        auditLogs = mock(AuditLogRepository.class);
        recruitmentClient = mock(RecruitmentServiceClient.class);
        interviewClient = mock(InterviewServiceClient.class);
        service = new AdminDashboardServiceImpl(users, auditLogs, recruitmentClient, interviewClient);
    }

    @Test
    void getDashboardAggregatesStatsAndHandlesDownstreamFallback() {
        when(users.count()).thenReturn(120L);
        when(users.countByCreatedAtAfter(any())).thenReturn(15L);
        when(users.countByRole(Role.CANDIDATE)).thenReturn(100L);
        when(users.countByRole(Role.RECRUITER)).thenReturn(18L);
        when(users.countByRole(Role.ADMIN)).thenReturn(2L);
        when(users.countByStatus(UserStatus.BANNED)).thenReturn(3L);
        when(recruitmentClient.adminStats()).thenReturn(new RecruitmentAdminStats(10, 2, 25, 1, 80, 40));
        when(interviewClient.adminStats()).thenThrow(new RuntimeException("interview-service down"));
        when(auditLogs.findTop20ByOrderByCreatedAtDescIdDesc()).thenReturn(List.of(
                AuditLog.builder().id(1).eventType("APPROVE_COMPANY").eventLabel("Duyệt công ty")
                        .badgeClass("badge b-ok").target("Lumen").actorEmail("admin@x.test")
                        .createdAt(LocalDateTime.now()).build()
        ));

        var res = service.getDashboard();
        assertEquals(5, res.kpis().size());
        assertEquals("120", res.kpis().get(0).value());
        assertEquals("10", res.kpis().get(1).value());
        assertEquals("0", res.kpis().get(4).value());
        assertEquals(3L, res.lockedUsersCount());
        assertEquals(1, res.activityLog().size());
    }

    @Test
    void recordAuditLogSavesEntity() {
        when(auditLogs.save(any(AuditLog.class))).thenAnswer(i -> {
            AuditLog log = i.getArgument(0);
            log.setId(9);
            log.setCreatedAt(LocalDateTime.now());
            return log;
        });

        var dto = service.recordAuditLog(new AuditLogCreateRequest(
                "LOCK_JOB", "Khoá tin", "badge b-danger", "Fake Job", 1, "admin@x.test"));
        assertEquals(9, dto.id());
        assertEquals("Khoá tin", dto.event());
        assertEquals("Fake Job", dto.target());
    }
}
