package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.EvaluationResult;

import java.time.LocalDateTime;
import java.util.Optional;

public interface EvaluationResultRepository extends JpaRepository<EvaluationResult, Integer> {
    Optional<EvaluationResult> findByResponseId(Integer responseId);

    @Query("SELECT AVG(e.predictedScore) FROM EvaluationResult e")
    Double averageScoreAll();

    @Query("""
            SELECT AVG(e.predictedScore) FROM EvaluationResult e
            JOIN e.response r
            JOIN r.sessionQuestion sq
            JOIN sq.session s
            WHERE s.recruiterUserId = :recruiterUserId
              AND s.completedAt >= :since
            """)
    Double averageScoreForRecruiter(@Param("recruiterUserId") Integer recruiterUserId,
                                    @Param("since") LocalDateTime since);
}
