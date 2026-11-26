package recruit.demo.entity;

import recruit.demo.enums.JobStatus;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "jobs")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Job {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "company_id", nullable = false)
    private Company company;

    @Column(name = "created_by", nullable = false)
    private Integer createdById;

    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(columnDefinition = "TEXT")
    private String requirements;

    @Column(columnDefinition = "TEXT")
    private String responsibilities;

    @Column(name = "employment_type")
    private String employmentType;

    @Column(name = "work_location")
    private String workLocation;

    @Column(name = "salary_min", precision = 14, scale = 2)
    private BigDecimal salaryMin;

    @Column(name = "salary_max", precision = 14, scale = 2)
    private BigDecimal salaryMax;

    @Column(nullable = false, length = 16)
    @Builder.Default
    private String currency = "VND";

    @Column(name = "experience_required", precision = 4, scale = 1)
    private BigDecimal experienceRequired;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    @Builder.Default
    private JobStatus status = JobStatus.DRAFT;

    @Column(name = "posted_at")
    private LocalDateTime postedAt;

    private LocalDateTime deadline;

    @Column(length = 64)
    private String level;

    private Integer headcount;

    @Column(columnDefinition = "TEXT")
    private String benefits;

    @Column(nullable = false)
    @Builder.Default
    private boolean hot = false;

    @Column(name = "default_interview_questions")
    @Builder.Default
    private Integer defaultInterviewQuestions = 5;

    @Column(name = "lock_reason")
    private String lockReason;

    @Column(name = "lock_note", columnDefinition = "TEXT")
    private String lockNote;

    @Column(name = "locked_at")
    private LocalDateTime lockedAt;

    @Column(name = "locked_by")
    private Integer lockedBy;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
