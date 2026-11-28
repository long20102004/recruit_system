package recruit.demo.controller;

import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.exception.ApiException;
import recruit.demo.service.JobService;

@RestController
@RequestMapping("/api/companies")
@RequiredArgsConstructor
public class PublicCompaniesController {
    private static final String COMPANIES = """
            SELECT c.id, c.name, c.description, c.website, c.address,
                   (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.id AND j.status = 'PUBLISHED' AND j.locked_at IS NULL
                     AND (j.deadline IS NULL OR j.deadline > CURRENT_TIMESTAMP)) AS jobs_count
            FROM companies c
            """;

    private final JdbcTemplate jdbc;
    private final JobService jobs;

    @GetMapping
    public List<CompanySummary> list() {
        return jdbc.query(COMPANIES + " ORDER BY jobs_count DESC, c.name, c.id",
                (row, index) -> company(row));
    }

    @GetMapping("/{id}")
    public CompanySummary detail(@PathVariable int id) {
        return jdbc.query(COMPANIES + " WHERE c.id = ?", (row, index) -> company(row), id)
                .stream().findFirst()
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy công ty."));
    }

    @GetMapping("/{id}/jobs")
    public BaseResponse<PageResponse<JobDtos.JobResponse>> jobs(@PathVariable int id,
            @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
        return BaseResponse.success(jobs.companyJobs(id, Paging.of(page, size)));
    }

    private static CompanySummary company(java.sql.ResultSet row) throws java.sql.SQLException {
        return new CompanySummary(row.getInt("id"), row.getString("name"), row.getString("description"),
                row.getString("website"), row.getString("address"), row.getLong("jobs_count"));
    }

    public record CompanySummary(int id, String name, String description, String website,
                                 String address, long openJobsCount) {}
}
