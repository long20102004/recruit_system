package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.ModelVersion;

import java.util.Optional;

public interface ModelVersionRepository extends JpaRepository<ModelVersion, Integer> {
    Optional<ModelVersion> findFirstByModuleNameAndActiveTrueOrderByCreatedAtDesc(String moduleName);
}
