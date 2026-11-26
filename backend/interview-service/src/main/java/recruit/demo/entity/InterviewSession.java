package recruit.demo.entity;

import recruit.demo.enums.SessionStatus;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "interview_sessions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class InterviewSession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name="candidate_id", nullable=false)
    private Integer candidateId;
    @Column(name="candidate_user_id", nullable=false)
    private Integer candidateUserId;
    @Column(name="recruiter_user_id")
    private Integer recruiterUserId;
    @Column(name="job_id")
    private Integer jobId;
    @Column(name="job_title")
    private String jobTitle;
    @Column(name="application_id")
    private Integer applicationId;

    private String title;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    @Builder.Default
    private SessionStatus status = SessionStatus.CREATED;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
