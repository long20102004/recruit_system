package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "interview_questions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class InterviewQuestion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name="created_by")
    private Integer createdById;

    private String title;
    @Column(name="external_key", length=80, unique=true)
    private String externalKey;
    private String skill;
    @Builder.Default
    private String seniority = "Junior";
    @Builder.Default
    private String source = "legacy";

    @Column(name = "question_text", nullable = false, columnDefinition = "TEXT")
    private String questionText;

    private String topic;
    private String difficulty;

    @Column(name = "question_type", nullable = false, length = 40)
    @Builder.Default
    private String questionType = "TEXT";

    @Column(name = "reference_answer", columnDefinition = "TEXT")
    private String referenceAnswer;

    @Column(name = "max_score", nullable = false, precision = 6, scale = 2)
    @Builder.Default
    private BigDecimal maxScore = new BigDecimal("10.0");

    @Column(name = "is_active", nullable = false)
    @Builder.Default
    private boolean active = true;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
