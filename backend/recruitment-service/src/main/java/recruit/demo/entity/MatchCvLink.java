package recruit.demo.entity;

import recruit.demo.enums.SyncStatus;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "match_cv_link")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MatchCvLink {
    @Id
    @Column(name = "candidate_id")
    private Integer candidateId;

    @Column(name = "cv_id", length = 64)
    private String cvId;

    @Column(name = "cv_version")
    private Integer cvVersion;

    @Column(name = "content_hash", length = 64)
    private String contentHash;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private SyncStatus status;

    @Column(columnDefinition = "TEXT")
    private String flags;

    @Column(name = "last_error", columnDefinition = "TEXT")
    private String lastError;

    @Builder.Default
    @Column(nullable = false)
    private int attempts = 0;

    @Column(name = "synced_at")
    private LocalDateTime syncedAt;

    @Column(name = "suggestion_cv_hash", length = 64)
    private String suggestionCvHash;

    @Column(name = "suggestion_catalog_hash", length = 64)
    private String suggestionCatalogHash;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
