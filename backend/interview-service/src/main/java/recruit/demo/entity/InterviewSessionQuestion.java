package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;

@Entity
@Table(name = "interview_session_questions", uniqueConstraints = @UniqueConstraint(columnNames = {"session_id", "question_order"}))
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class InterviewSessionQuestion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "session_id", nullable = false)
    private InterviewSession session;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "question_id", nullable = false)
    private InterviewQuestion question;

    @Column(name = "question_order", nullable = false)
    private int questionOrder;

    @Column(name = "max_score", nullable = false, precision = 6, scale = 2)
    @Builder.Default
    private BigDecimal maxScore = new BigDecimal("5.0");

    @Column(name = "time_limit_seconds")
    private Integer timeLimitSeconds;
}
