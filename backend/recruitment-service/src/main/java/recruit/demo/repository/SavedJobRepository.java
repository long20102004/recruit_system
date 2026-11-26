package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.SavedJob;

import java.util.List;
import java.util.Optional;

public interface SavedJobRepository extends JpaRepository<SavedJob, Integer> {

    @Query("""
            SELECT s FROM SavedJob s
            JOIN FETCH s.job j
            JOIN FETCH j.company
            WHERE s.candidate.id = :candidateId
            ORDER BY s.savedAt DESC
            """)
    List<SavedJob> findByCandidateIdOrderBySavedAtDesc(@Param("candidateId") Integer candidateId);

    Optional<SavedJob> findByCandidateIdAndJobId(Integer candidateId, Integer jobId);

    boolean existsByCandidateIdAndJobId(Integer candidateId, Integer jobId);

    long countByCandidateId(Integer candidateId);
}
