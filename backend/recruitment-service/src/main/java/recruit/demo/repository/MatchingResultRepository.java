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

    Optional<MatchingResult> findFirstByJobIdAndCandidateIdAndModelNameAndModelVersionOrderByCreatedAtDesc(
            Integer jobId, Integer candidateId, String modelName, String modelVersion);
}
