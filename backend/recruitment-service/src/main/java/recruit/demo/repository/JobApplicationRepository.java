package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.JobApplication;

import java.util.List;
import java.util.Optional;

public interface JobApplicationRepository extends JpaRepository<JobApplication, Integer> {

    Optional<JobApplication> findByJobIdAndCandidateId(Integer jobId, Integer candidateId);

    @Query("""
            SELECT a FROM JobApplication a
            JOIN FETCH a.job j
            JOIN FETCH j.company
            JOIN FETCH a.candidate c
            WHERE a.candidate.id = :candidateId
            ORDER BY a.appliedAt DESC
            """)
    List<JobApplication> findByCandidateIdOrderByAppliedAtDesc(@Param("candidateId") Integer candidateId);

    @Query("""
            SELECT a FROM JobApplication a
            JOIN FETCH a.job j
            JOIN FETCH j.company
            JOIN FETCH a.candidate c
            WHERE j.createdById = :userId
            ORDER BY a.appliedAt DESC
            """)
    List<JobApplication> findForRecruiterUser(@Param("userId") Integer userId);

    long countByJobCreatedById(Integer userId);

    List<JobApplication> findByJobId(Integer jobId);
}
