package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.JobApplication;
import recruit.demo.enums.ApplicationStatus;

import java.time.LocalDateTime;
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

    @Query(value = """
            SELECT a FROM JobApplication a
            JOIN FETCH a.job j
            JOIN FETCH j.company
            JOIN FETCH a.candidate c
            WHERE j.createdById = :userId
              AND (:status IS NULL OR a.status = :status)
              AND (:jobId IS NULL OR j.id = :jobId)
            ORDER BY a.appliedAt DESC
            """,
            countQuery = """
            SELECT count(a) FROM JobApplication a
            JOIN a.job j
            WHERE j.createdById = :userId
              AND (:status IS NULL OR a.status = :status)
              AND (:jobId IS NULL OR j.id = :jobId)
            """)
    Page<JobApplication> findForRecruiterFiltered(@Param("userId") Integer userId,
                                                  @Param("status") ApplicationStatus status,
                                                  @Param("jobId") Integer jobId,
                                                  Pageable pageable);

    long countByJobCreatedById(Integer userId);

    long countByJobCreatedByIdAndStatus(Integer userId, ApplicationStatus status);

    long countByJobCreatedByIdAndAppliedAtBetween(Integer userId, LocalDateTime start, LocalDateTime end);

    long countByJobCreatedByIdAndStatusAndAppliedAtBetween(Integer userId, ApplicationStatus status,
                                                           LocalDateTime start, LocalDateTime end);

    long countByAppliedAtBetween(LocalDateTime start, LocalDateTime end);

    long countByJobId(Integer jobId);

    List<JobApplication> findByJobId(Integer jobId);
}
