package recruit.demo.controller;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.exception.ApiException;
import recruit.demo.security.SecurityUtils;

@RestController
@RequestMapping("/api/jobs/saved")
@PreAuthorize("hasAuthority('application:read-own')")
@RequiredArgsConstructor
public class SavedJobsController {
    private final JdbcTemplate jdbc;

    @GetMapping
    public List<SavedJob> list() {
        return jdbc.query("""
                SELECT j.id, j.title, c.name AS company, j.work_location, j.deadline,
                       s.saved_at, j.status = 'PUBLISHED' AND j.locked_at IS NULL
                           AND (j.deadline IS NULL OR j.deadline > CURRENT_TIMESTAMP) AS is_open
                FROM saved_jobs s
                JOIN jobs j ON j.id = s.job_id
                JOIN companies c ON c.id = j.company_id
                WHERE s.user_id = ?
                ORDER BY s.saved_at DESC, j.id DESC
                """, (row, index) -> new SavedJob(row.getInt("id"), row.getString("title"),
                row.getString("company"), row.getString("work_location"),
                row.getObject("deadline", LocalDateTime.class),
                row.getObject("saved_at", LocalDateTime.class), row.getBoolean("is_open")), userId());
    }

    @GetMapping("/{jobId}")
    public Map<String, Boolean> status(@PathVariable int jobId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM saved_jobs WHERE user_id = ? AND job_id = ?",
                Integer.class, userId(), jobId);
        return Map.of("saved", count != null && count > 0);
    }

    @PutMapping("/{jobId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void save(@PathVariable int jobId) {
        int userId = userId();
        if (status(jobId).get("saved")) return;
        int changed = jdbc.update("""
                INSERT INTO saved_jobs (user_id, job_id)
                SELECT ?, id FROM jobs WHERE id = ? AND status = 'PUBLISHED' AND locked_at IS NULL
                    AND (deadline IS NULL OR deadline > CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE saved_at = saved_jobs.saved_at
                """, userId, jobId);
        if (changed == 0 && !status(jobId).get("saved")) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Tin tuyển dụng hiện không mở.");
        }
    }

    @DeleteMapping("/{jobId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void remove(@PathVariable int jobId) {
        jdbc.update("DELETE FROM saved_jobs WHERE user_id = ? AND job_id = ?", userId(), jobId);
    }

    private int userId() {
        return SecurityUtils.currentUser().getId();
    }

    public record SavedJob(int id, String title, String company, String location,
                           LocalDateTime deadline, LocalDateTime savedAt, boolean open) {}
}
