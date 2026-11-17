package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.Setting;

import java.util.List;

public interface SettingRepository extends JpaRepository<Setting, Integer> {
    List<Setting> findByName(String name);
}
