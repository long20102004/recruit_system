package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.Company;
import recruit.demo.enums.CompanyStatus;

import java.util.List;
import java.util.Optional;

public interface CompanyRepository extends JpaRepository<Company, Integer> {
    @Modifying
    @Query(value = "INSERT IGNORE INTO companies (name) VALUES (:name)", nativeQuery = true)
    void insertIfAbsent(@Param("name") String name);

    Optional<Company> findByNameIgnoreCase(String name);

    long countByStatus(CompanyStatus status);

    @Query("""
            SELECT c FROM Company c
            WHERE (:status IS NULL OR c.status = :status)
              AND (:city IS NULL OR LOWER(COALESCE(c.city, c.address, '')) LIKE LOWER(CONCAT('%', :city, '%')))
              AND (:industry IS NULL OR LOWER(COALESCE(c.industry, '')) = LOWER(:industry))
              AND (:q IS NULL OR LOWER(c.name) LIKE LOWER(CONCAT('%', :q, '%'))
                   OR LOWER(COALESCE(c.displayName, '')) LIKE LOWER(CONCAT('%', :q, '%'))
                   OR LOWER(COALESCE(c.legalName, '')) LIKE LOWER(CONCAT('%', :q, '%'))
                   OR LOWER(COALESCE(c.taxCode, '')) LIKE LOWER(CONCAT('%', :q, '%'))
                   OR LOWER(COALESCE(c.tagline, '')) LIKE LOWER(CONCAT('%', :q, '%'))
                   OR LOWER(COALESCE(c.techStack, '')) LIKE LOWER(CONCAT('%', :q, '%')))
            ORDER BY c.submittedAt DESC, c.createdAt DESC, c.id DESC
            """)
    List<Company> search(@Param("status") CompanyStatus status,
                         @Param("city") String city,
                         @Param("industry") String industry,
                         @Param("q") String q);
}
