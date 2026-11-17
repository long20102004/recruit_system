package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "evaluation_rubrics")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class EvaluationRubric {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "question_id", nullable = false)
    private InterviewQuestion question;

    @Column(name = "criterion_name", nullable = false)
    private String criterionName;

    @Column(name = "criterion_description", columnDefinition = "TEXT")
    private String criterionDescription;

    @Column(name = "max_score", precision = 6, scale = 2)
    private BigDecimal maxScore;

    @Column(nullable = false, precision = 6, scale = 4)
    @Builder.Default
    private BigDecimal weight = BigDecimal.ONE;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "expected_keywords", columnDefinition = "json")
    private List<String> expectedKeywords;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name="reference_answers", columnDefinition="json")
    private List<String> referenceAnswers;
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition="json")
    private List<String> misconceptions;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
