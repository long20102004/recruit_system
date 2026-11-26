package recruit.demo.service;

import recruit.demo.dto.ServiceDtos.AuditLogCreateRequest;
import recruit.demo.dto.admin.AdminDashboardDtos.AdminActivityLogDto;
import recruit.demo.dto.admin.AdminDashboardDtos.AdminDashboardResponse;

public interface AdminDashboardService {
    AdminDashboardResponse getDashboard();
    AdminActivityLogDto recordAuditLog(AuditLogCreateRequest request);
}
