package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.Company;

import java.util.Optional;

public interface CompanyRepository extends JpaRepository<Company, Integer> {
    @org.springframework.data.jpa.repository.Modifying
    @org.springframework.data.jpa.repository.Query(value="INSERT IGNORE INTO companies (name) VALUES (:name)", nativeQuery=true)
    void insertIfAbsent(@org.springframework.data.repository.query.Param("name") String name);

    Optional<Company> findByNameIgnoreCase(String name);
}
