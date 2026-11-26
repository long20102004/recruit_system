package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "audit_logs")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "event_type", nullable = false, length = 64)
    private String eventType;

    @Column(name = "event_label", nullable = false, length = 120)
    private String eventLabel;

    @Column(name = "badge_class", nullable = false, length = 64)
    @Builder.Default
    private String badgeClass = "badge b-brand";

    @Column(nullable = false)
    private String target;

    @Column(name = "actor_user_id")
    private Integer actorUserId;

    @Column(name = "actor_email", nullable = false)
    private String actorEmail;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
