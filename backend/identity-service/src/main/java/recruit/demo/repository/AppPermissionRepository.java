package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.AppPermission;

public interface AppPermissionRepository extends JpaRepository<AppPermission, String> {
}
