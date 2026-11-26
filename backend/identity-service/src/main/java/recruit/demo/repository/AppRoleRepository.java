package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.AppRole;

public interface AppRoleRepository extends JpaRepository<AppRole, String> {
}
