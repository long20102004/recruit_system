package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.CompanyFollower;

import java.util.Optional;

public interface CompanyFollowerRepository extends JpaRepository<CompanyFollower, Integer> {
    Optional<CompanyFollower> findByCompanyIdAndUserId(Integer companyId, Integer userId);
    boolean existsByCompanyIdAndUserId(Integer companyId, Integer userId);
    long countByCompanyId(Integer companyId);
}
