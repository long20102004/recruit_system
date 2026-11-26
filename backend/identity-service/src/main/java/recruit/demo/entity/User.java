package recruit.demo.entity;

import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "users")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "full_name", nullable = false)
    private String fullName;

    @Column(nullable = false, length = 255)
    private String email;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    private String phone;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    @Builder.Default
    private Role role = Role.CANDIDATE;

    @Column(name = "role_chosen", nullable = false)
    @Builder.Default
    private boolean roleChosen = false;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    @Builder.Default
    private UserStatus status = UserStatus.ACTIVE;

    /** NULL = chưa xác thực email. */
    @Column(name = "email_verified_at")
    private LocalDateTime emailVerifiedAt;

    @Column(name = "locked_reason", length = 500)
    private String lockedReason;

    @Column(name = "locked_at")
    private LocalDateTime lockedAt;

    /** JWT có iat trước mốc này bị từ chối ở mọi service. */
    @Column(name = "sessions_valid_after")
    private LocalDateTime sessionsValidAfter;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public boolean emailVerified() {
        return emailVerifiedAt != null;
    }

    /** Mốc vô hiệu phiên dạng epoch giây (so với JWT iat); null nếu chưa đặt. */
    public Long sessionsValidAfterEpochSeconds() {
        return sessionsValidAfter == null ? null
                : sessionsValidAfter.atZone(java.time.ZoneId.systemDefault()).toEpochSecond();
    }

    /** Vô hiệu mọi JWT đã phát hành tới thời điểm hiện tại. */
    public void invalidateSessions() {
        sessionsValidAfter = LocalDateTime.now().withNano(0);
    }
}
