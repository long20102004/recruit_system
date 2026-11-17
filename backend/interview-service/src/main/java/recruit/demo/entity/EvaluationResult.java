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
@Table(name = "evaluation_results")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class EvaluationResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "response_id", nullable = false, unique = true)
    private InterviewResponse response;

    @Column(name = "evaluation_method", nullable = false, length = 40)
    @Builder.Default
    private String evaluationMethod = "RULE_BASED";

    @Column(name = "bertscore_precision", precision = 6, scale = 4)
    private BigDecimal bertscorePrecision;

    @Column(name = "bertscore_recall", precision = 6, scale = 4)
    private BigDecimal bertscoreRecall;

    @Column(name = "bertscore_f1", precision = 6, scale = 4)
    private BigDecimal bertscoreF1;

    @Column(name = "predicted_score", nullable = false, precision = 6, scale = 2)
    private BigDecimal predictedScore;

    @Column(name = "human_score", precision = 6, scale = 2)
    private BigDecimal humanScore;

    @Column(name = "correctness_score", precision = 6, scale = 2)
    private BigDecimal correctnessScore;

    @Column(name = "completeness_score", precision = 6, scale = 2)
    private BigDecimal completenessScore;

    @Column(columnDefinition = "TEXT")
    private String feedback;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    private List<String> strengths;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "missing_points", columnDefinition = "json")
    private List<String> missingPoints;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "model_version_id")
    private ModelVersion modelVersion;

    @Column(name="scoring_mode", length=32)
    private String scoringMode;
    @Column(name="scoring_model_version")
    private String scoringModelVersion;
    @Column(name="coverage_score", precision=6, scale=4)
    private BigDecimal coverageScore;
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name="criterion_results", columnDefinition="json")
    private List<java.util.Map<String,Object>> criterionResults;

    @CreationTimestamp
    @Column(name = "evaluated_at", nullable = false, updatable = false)
    private LocalDateTime evaluatedAt;
}
