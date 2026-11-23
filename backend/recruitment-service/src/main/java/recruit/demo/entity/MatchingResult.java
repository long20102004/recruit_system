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
@Table(name = "matching_results")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MatchingResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "candidate_id", nullable = false)
    private CandidateProfile candidate;

    @Column(name = "cv_id")
    private Integer cvId;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "job_id", nullable = false)
    private Job job;

    @Column(name = "semantic_score", precision = 6, scale = 4)
    private BigDecimal semanticScore;

    @Column(name = "skills_score", precision = 6, scale = 4)
    private BigDecimal skillsScore;

    @Column(name = "experience_score", precision = 6, scale = 4)
    private BigDecimal experienceScore;

    @Column(name = "overall_score", nullable = false, precision = 6, scale = 4)
    private BigDecimal overallScore;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "matched_skills", columnDefinition = "json")
    private List<String> matchedSkills;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "missing_skills", columnDefinition = "json")
    private List<String> missingSkills;

    @Column(columnDefinition = "TEXT")
    private String explanation;

    @Column(name = "model_name")
    private String modelName;

    @Column(name = "model_version")
    private String modelVersion;

    /** cvmatch; 'legacy' = dong cua dich vu cv-matching-ai cu (da go), khong con hien. */
    @Builder.Default
    @Column(nullable = false, length = 16)
    private String engine = "legacy";

    /** cvmatch: jd_to_cv (recruiter) | cv_to_jd (ung vien). */
    @Column(length = 16)
    private String direction;

    @Column(length = 8)
    private String band;

    @Column(name = "cap_applied")
    private Boolean capApplied;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    private List<String> flags;

    @Column(name = "rank_position")
    private Integer rankPosition;

    @Column(name = "run_id", length = 64)
    private String runId;

    @Column(name = "cvmatch_cv_id", length = 64)
    private String cvmatchCvId;

    /** sections cua giai thich cvmatch (luu lan dau lay). */
    @Column(name = "explanation_json", columnDefinition = "json")
    @JdbcTypeCode(SqlTypes.JSON)
    private java.util.Map<String, Object> explanationJson;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
