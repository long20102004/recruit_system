package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.Job;
import recruit.demo.enums.JobStatus;

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

    long countByStatusAndCreatedById(JobStatus status, Integer userId);

    @Query(value = """
            SELECT j FROM Job j
            JOIN FETCH j.company
            WHERE (:status IS NULL OR j.status = :status)
              AND (:keyword IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.description) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.company.name) LIKE LOWER(CONCAT('%', :keyword, '%')))
              AND (:city IS NULL OR LOWER(j.workLocation) LIKE LOWER(CONCAT('%', :city, '%')))
            ORDER BY j.postedAt DESC, j.createdAt DESC
            """,
            countQuery = """
            SELECT count(j) FROM Job j
            WHERE (:status IS NULL OR j.status = :status)
              AND (:keyword IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.description) LIKE LOWER(CONCAT('%', :keyword, '%'))
                   OR LOWER(j.company.name) LIKE LOWER(CONCAT('%', :keyword, '%')))
              AND (:city IS NULL OR LOWER(j.workLocation) LIKE LOWER(CONCAT('%', :city, '%')))
            """)
    Page<Job> search(@Param("keyword") String keyword,
                     @Param("city") String city,
                     @Param("status") JobStatus status,
                     Pageable pageable);
}
