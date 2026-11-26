package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.ServiceDtos.AuditLogCreateRequest;
import recruit.demo.dto.admin.AdminDashboardDtos.AdminActivityLogDto;
import recruit.demo.dto.admin.AdminDashboardDtos.AdminDashboardResponse;
import recruit.demo.service.AdminDashboardService;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN') or hasAuthority('dashboard:admin') or hasAuthority('user:read')")
public class AdminDashboardController {

    private final AdminDashboardService dashboardService;

    @GetMapping("/dashboard")
    public BaseResponse<AdminDashboardResponse> dashboard() {
        return BaseResponse.success(dashboardService.getDashboard());
    }

    @PostMapping("/audit-logs")
    public BaseResponse<AdminActivityLogDto> recordAudit(@RequestBody AuditLogCreateRequest request) {
        return BaseResponse.success(dashboardService.recordAuditLog(request));
    }
}
