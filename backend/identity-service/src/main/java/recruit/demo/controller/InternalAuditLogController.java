package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import recruit.demo.dto.ServiceDtos.AuditLogCreateRequest;
import recruit.demo.service.AdminDashboardService;

@RestController
@RequiredArgsConstructor
public class InternalAuditLogController {

    private final AdminDashboardService dashboardService;

    @PostMapping("/internal/audit-logs")
    public void record(@RequestBody AuditLogCreateRequest request) {
        dashboardService.recordAuditLog(request);
    }
}
