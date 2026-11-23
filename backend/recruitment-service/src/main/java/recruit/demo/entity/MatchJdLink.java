package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "match_jd_link")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MatchJdLink {
    @Id
    @Column(name = "job_id")
    private Integer jobId;

    @Column(name = "jd_id", nullable = false, length = 64)
    private String jdId;

    @Column(name = "jd_version")
    private Integer jdVersion;

    @Column(name = "content_hash", length = 64)
    private String contentHash;

    @Column(name = "jd_status", length = 16)
    private String jdStatus;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private SyncStatus status;

    @Column(name = "last_error", columnDefinition = "TEXT")
    private String lastError;

    @Builder.Default
    @Column(nullable = false)
    private int attempts = 0;

    @Column(name = "synced_at")
    private LocalDateTime syncedAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
