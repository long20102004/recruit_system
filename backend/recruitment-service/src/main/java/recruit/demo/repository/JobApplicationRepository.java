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

    @org.springframework.data.jpa.repository.Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from JobApplication a where a.id = :id")
    Optional<JobApplication> findForUpdate(@Param("id") Integer id);

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
            WHERE j.createdById = :userId AND EXISTS (
                SELECT rp.id FROM RecruiterProfile rp WHERE rp.userId = :userId AND rp.company = j.company
            )
            AND (:resultsOnly = false OR a.interviewScore IS NOT NULL)
            ORDER BY a.appliedAt DESC
            """,
            countQuery = """
            SELECT count(a) FROM JobApplication a
            JOIN a.job j
            WHERE j.createdById = :userId AND EXISTS (
                SELECT rp.id FROM RecruiterProfile rp WHERE rp.userId = :userId AND rp.company = j.company
            )
            AND (:resultsOnly = false OR a.interviewScore IS NOT NULL)
            """)
    Page<JobApplication> findForRecruiterUser(@Param("userId") Integer userId,
            @Param("resultsOnly") boolean resultsOnly, Pageable pageable);

    interface RankedApplication {
        JobApplication getApplication();
        java.math.BigDecimal getRankingScore();
    }

    @Query(value = """
            SELECT a AS application,
                CASE WHEN m.overallScore IS NOT NULL AND a.interviewScore IS NOT NULL
                     AND j.status = recruit.demo.enums.JobStatus.PUBLISHED
                     AND (j.deadline IS NULL OR j.deadline > CURRENT_TIMESTAMP)
                     AND EXISTS (SELECT cv.id FROM CvData cv WHERE cv.candidateId = a.candidate.id
                         AND cv.field = 'parsing_status' AND cv.value = 'COMPLETED')
                     THEN m.overallScore * (1 - :interviewWeight) + a.interviewScore * :interviewWeight / 10
                     ELSE NULL END AS rankingScore
            FROM JobApplication a
            JOIN a.job j
            LEFT JOIN MatchingResult m ON m.job = j AND m.candidate = a.candidate
                AND m.engine = 'cvmatch' AND m.direction = 'jd_to_cv'
                AND m.id = (SELECT MAX(currentMatch.id) FROM MatchingResult currentMatch
                    WHERE currentMatch.job = j AND currentMatch.candidate = a.candidate
                        AND currentMatch.engine = 'cvmatch' AND currentMatch.direction = 'jd_to_cv')
            WHERE j.createdById = :userId AND EXISTS (
                SELECT rp.id FROM RecruiterProfile rp WHERE rp.userId = :userId AND rp.company = j.company
            )
            ORDER BY rankingScore DESC NULLS LAST, a.appliedAt DESC, a.id DESC
            """, countQuery = """
            SELECT count(a) FROM JobApplication a JOIN a.job j
            WHERE j.createdById = :userId AND EXISTS (
                SELECT rp.id FROM RecruiterProfile rp WHERE rp.userId = :userId AND rp.company = j.company
            )
            """)
    Page<RankedApplication> rankForRecruiter(@Param("userId") Integer userId,
            @Param("interviewWeight") java.math.BigDecimal interviewWeight, Pageable pageable);

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

    /** cv_id của các đơn có trạng thái trong danh sách (dùng chặn xoá CV đang ứng tuyển). */
    @Query("SELECT DISTINCT a.cvId FROM JobApplication a WHERE a.candidate.id = :candidateId AND a.cvId IS NOT NULL AND a.status IN :statuses")
    List<Integer> findCvIdsByCandidateIdAndStatusIn(@Param("candidateId") Integer candidateId,
                                                     @Param("statuses") java.util.Collection<ApplicationStatus> statuses);

    List<JobApplication> findByJobId(Integer jobId);
}
