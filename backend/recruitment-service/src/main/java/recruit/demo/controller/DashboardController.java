package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import recruit.demo.dto.DashboardDtos;
import recruit.demo.service.DashboardService;

@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final DashboardService dashboardService;

    @GetMapping("/recruiter")
    @PreAuthorize("hasAuthority('dashboard:recruiter')")
    public DashboardDtos.RecruiterStatsResponse recruiterStats(
            @RequestParam(defaultValue = "30") int days
    ) {
        return dashboardService.recruiterStats(days);
    }
}
