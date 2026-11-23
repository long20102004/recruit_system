package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.EvaluationResult;

import java.util.Optional;

public interface EvaluationResultRepository extends JpaRepository<EvaluationResult, Integer> {
    Optional<EvaluationResult> findByResponseId(Integer responseId);
}
