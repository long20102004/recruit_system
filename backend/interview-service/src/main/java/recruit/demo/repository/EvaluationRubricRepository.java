package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.EvaluationRubric;

import java.util.List;

public interface EvaluationRubricRepository extends JpaRepository<EvaluationRubric, Integer> {
    List<EvaluationRubric> findByQuestionId(Integer questionId);
}
