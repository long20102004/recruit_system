package recruit.demo.controller;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.security.SecurityUtils;

@RestController
@RequestMapping("/api/applications/mine/notifications")
@PreAuthorize("hasAuthority('application:read-own')")
@RequiredArgsConstructor
public class ApplicationNotificationsController {
    private static final String OWNED = """
             JOIN job_applications a ON a.id = h.application_id
             JOIN candidate_profiles p ON p.id = a.candidate_id
             JOIN jobs j ON j.id = a.job_id
             WHERE p.user_id = ? AND h.status <> 'WITHDRAWN'
            """;
    private final JdbcTemplate jdbc;

    @GetMapping
    public List<Notification> list(@RequestParam(required = false) Long before) {
        return jdbc.query("""
                SELECT h.id, j.title, h.status, h.changed_at, h.read_at IS NULL AS unread
                FROM application_status_history h
                """ + OWNED + """
                AND h.id < ?
                ORDER BY h.id DESC LIMIT 20
                """, (row, index) -> new Notification(row.getLong("id"), row.getString("title"),
                row.getString("status"), row.getObject("changed_at", LocalDateTime.class), row.getBoolean("unread")),
                userId(), before == null ? Long.MAX_VALUE : before);
    }

    @GetMapping("/unread")
    public Map<String, Long> unread() {
        Long count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM application_status_history h " + OWNED + " AND h.read_at IS NULL",
                Long.class, userId());
        return Map.of("count", count == null ? 0L : count);
    }

    @PatchMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void read(@PathVariable long id) {
        jdbc.update("""
                UPDATE application_status_history h
                JOIN job_applications a ON a.id = h.application_id
                JOIN candidate_profiles p ON p.id = a.candidate_id
                SET h.read_at = CURRENT_TIMESTAMP(6)
                WHERE p.user_id = ? AND h.id = ? AND h.read_at IS NULL AND h.status <> 'WITHDRAWN'
                """, userId(), id);
    }

    private int userId() {
        return SecurityUtils.currentUser().getId();
    }

    public record Notification(long id, String title, String status, LocalDateTime changedAt, boolean unread) {}
}
