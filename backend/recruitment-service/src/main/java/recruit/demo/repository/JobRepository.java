package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.Job;
import recruit.demo.enums.JobStatus;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public interface JobRepository extends JpaRepository<Job, Integer> {

    @Query(value = """
            SELECT j FROM Job j
            JOIN FETCH j.company
            WHERE j.createdById = :userId
            ORDER BY j.createdAt DESC
            """,
            countQuery = """
            SELECT count(j) FROM Job j
            WHERE j.createdById = :userId
            """)
    Page<Job> findByCreatedByIdOrderByCreatedAtDesc(@Param("userId") Integer userId, Pageable pageable);

    @Query(value = """
            SELECT j FROM Job j
            JOIN FETCH j.company
            WHERE j.company.id = :companyId
            ORDER BY j.createdAt DESC
            """,
            countQuery = """
            SELECT count(j) FROM Job j
            WHERE j.company.id = :companyId
            """)
    Page<Job> findByCompanyIdOrderByCreatedAtDesc(@Param("companyId") Integer companyId, Pageable pageable);

    long countByStatusAndCreatedById(JobStatus status, Integer userId);

    long countByCompanyIdAndStatus(Integer companyId, JobStatus status);

    long countByStatus(JobStatus status);

    List<Job> findByStatusAndDeadlineBefore(JobStatus status, LocalDateTime now);

    List<Job> findByCreatedByIdAndStatusAndDeadlineBetweenOrderByDeadlineAsc(
            Integer userId, JobStatus status, LocalDateTime start, LocalDateTime end);

    List<Job> findByStatus(JobStatus status);

    @Query(value = """
            SELECT j FROM Job j
            JOIN FETCH j.company
            WHERE (:status IS NULL OR j.status = :status)
              AND (:keyword IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.description) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.company.name) LIKE LOWER(CONCAT('%', :keyword, '%')))
              AND (:city IS NULL OR LOWER(j.workLocation) LIKE LOWER(CONCAT('%', :city, '%')))
              AND (:minSalary IS NULL OR COALESCE(j.salaryMax, j.salaryMin, 0) >= :minSalary)
            ORDER BY j.postedAt DESC, j.createdAt DESC
            """,
            countQuery = """
            SELECT count(j) FROM Job j
            WHERE (:status IS NULL OR j.status = :status)
              AND (:keyword IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.description) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.company.name) LIKE LOWER(CONCAT('%', :keyword, '%')))
              AND (:city IS NULL OR LOWER(j.workLocation) LIKE LOWER(CONCAT('%', :city, '%')))
              AND (:minSalary IS NULL OR COALESCE(j.salaryMax, j.salaryMin, 0) >= :minSalary)
            """)
    Page<Job> search(@Param("keyword") String keyword,
                     @Param("city") String city,
                     @Param("status") JobStatus status,
                     @Param("minSalary") BigDecimal minSalary,
                     Pageable pageable);

    @Query(value = """
            SELECT j FROM Job j
            JOIN FETCH j.company c
            WHERE (:status IS NULL OR j.status = :status)
              AND (:companyId IS NULL OR c.id = :companyId)
              AND (:keyword IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(c.name) LIKE LOWER(CONCAT('%', :keyword, '%')))
            ORDER BY j.createdAt DESC
            """,
            countQuery = """
            SELECT count(j) FROM Job j
            JOIN j.company c
            WHERE (:status IS NULL OR j.status = :status)
              AND (:companyId IS NULL OR c.id = :companyId)
              AND (:keyword IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(c.name) LIKE LOWER(CONCAT('%', :keyword, '%')))
            """)
    Page<Job> adminSearch(@Param("status") JobStatus status,
                          @Param("companyId") Integer companyId,
                          @Param("keyword") String keyword,
                          Pageable pageable);
}
