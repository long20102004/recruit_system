package recruit.demo.cvtemplate;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface CvTemplateRepository extends JpaRepository<CvTemplate, Integer> {

    List<CvTemplate> findAllByOrderByDefaultTemplateDescIdAsc();

    List<CvTemplate> findByStatusOrderByDefaultTemplateDescIdAsc(CvTemplateStatus status);

    Optional<CvTemplate> findFirstByDefaultTemplateTrue();

    boolean existsByNameIgnoreCase(String name);

    boolean existsByNameIgnoreCaseAndIdNot(String name, Integer id);
}
