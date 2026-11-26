package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.ApplicationNote;

import java.util.Optional;

public interface ApplicationNoteRepository extends JpaRepository<ApplicationNote, Integer> {
    Optional<ApplicationNote> findByApplicationId(Integer applicationId);
}
