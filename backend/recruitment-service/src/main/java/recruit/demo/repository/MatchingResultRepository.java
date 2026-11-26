package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.MatchingResult;

import java.util.List;
import java.util.Optional;

public interface MatchingResultRepository extends JpaRepository<MatchingResult, Integer> {

    @Query("""
            SELECT m FROM MatchingResult m
            JOIN FETCH m.job j
            JOIN FETCH j.company
            JOIN FETCH m.candidate c
            WHERE m.candidate.id = :candidateId
            ORDER BY m.overallScore DESC, m.createdAt DESC
            """)
    List<MatchingResult> findByCandidateId(@Param("candidateId") Integer candidateId);

    @Query("""
            SELECT m FROM MatchingResult m
            JOIN FETCH m.candidate c
            JOIN FETCH m.job j
            JOIN FETCH j.company
            WHERE m.job.id = :jobId
            ORDER BY m.overallScore DESC, m.createdAt DESC
            """)
    List<MatchingResult> findByJobId(@Param("jobId") Integer jobId);

    @Query("""
            SELECT m FROM MatchingResult m
            JOIN FETCH m.job j
            JOIN FETCH j.company
            JOIN FETCH m.candidate c
            WHERE m.candidate.id = :candidateId AND m.engine = :engine
              AND (:direction IS NULL OR m.direction = :direction)
            ORDER BY m.overallScore DESC, m.createdAt DESC
            """)
    List<MatchingResult> findByCandidateAndEngine(@Param("candidateId") Integer candidateId,
                                                  @Param("engine") String engine,
                                                  @Param("direction") String direction);

    @Query("""
            SELECT m FROM MatchingResult m
            JOIN FETCH m.candidate c
            JOIN FETCH m.job j
            JOIN FETCH j.company
            WHERE m.job.id = :jobId AND m.engine = :engine
              AND (:direction IS NULL OR m.direction = :direction)
            ORDER BY m.overallScore DESC, m.createdAt DESC
            """)
    List<MatchingResult> findByJobAndEngine(@Param("jobId") Integer jobId, @Param("engine") String engine,
                                            @Param("direction") String direction);

    Optional<MatchingResult> findFirstByJobIdAndCandidateIdAndEngineAndDirection(Integer jobId, Integer candidateId,
                                                                               String engine, String direction);

    Optional<MatchingResult> findFirstByJobIdAndCandidateIdAndModelNameAndModelVersionOrderByCreatedAtDesc(
            Integer jobId, Integer candidateId, String modelName, String modelVersion);

    Optional<MatchingResult> findFirstByJobIdAndCandidateIdOrderByCreatedAtDesc(Integer jobId, Integer candidateId);
}
