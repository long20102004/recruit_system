package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.JobApplication;

import java.util.List;
import java.util.Optional;

public interface JobApplicationRepository extends JpaRepository<JobApplication, Integer> {

    Optional<JobApplication> findByJobIdAndCandidateId(Integer jobId, Integer candidateId);

    @Query(value = """
            SELECT a FROM JobApplication a
            JOIN FETCH a.job j
            JOIN FETCH j.company
            JOIN FETCH a.candidate c
            WHERE a.candidate.id = :candidateId
            ORDER BY a.appliedAt DESC
            """,
            countQuery = """
            SELECT count(a) FROM JobApplication a
            WHERE a.candidate.id = :candidateId
            """)
    Page<JobApplication> findByCandidateIdOrderByAppliedAtDesc(@Param("candidateId") Integer candidateId, Pageable pageable);

    @Query(value = """
            SELECT a FROM JobApplication a
            JOIN FETCH a.job j
            JOIN FETCH j.company
            JOIN FETCH a.candidate c
            WHERE j.createdById = :userId
            ORDER BY a.appliedAt DESC
            """,
            countQuery = """
            SELECT count(a) FROM JobApplication a
            JOIN a.job j
            WHERE j.createdById = :userId
            """)
    Page<JobApplication> findForRecruiterUser(@Param("userId") Integer userId, Pageable pageable);

    long countByJobCreatedById(Integer userId);

    List<JobApplication> findByJobId(Integer jobId);
}
