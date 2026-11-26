package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.ApplicationStatusHistory;

import java.util.List;

public interface ApplicationStatusHistoryRepository extends JpaRepository<ApplicationStatusHistory, Integer> {
    List<ApplicationStatusHistory> findByApplicationIdOrderByCreatedAtDescIdDesc(Integer applicationId);
}
