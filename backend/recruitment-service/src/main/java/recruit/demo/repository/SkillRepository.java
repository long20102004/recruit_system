package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.Skill;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface SkillRepository extends JpaRepository<Skill, Integer> {
    Optional<Skill> findByNameIgnoreCase(String name);
    List<Skill> findByNameIgnoreCaseIn(Collection<String> names);
}
