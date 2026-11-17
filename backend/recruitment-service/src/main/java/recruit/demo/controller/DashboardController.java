package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import recruit.demo.dto.DashboardDtos;
import recruit.demo.service.DashboardService;

@RestController
@RequestMapping("/api/dashboard")
@RequiredArgsConstructor
public class DashboardController {

    private final DashboardService dashboardService;

    @GetMapping("/recruiter")
    public DashboardDtos.RecruiterStatsResponse recruiterStats() {
        return dashboardService.recruiterStats();
    }
}
