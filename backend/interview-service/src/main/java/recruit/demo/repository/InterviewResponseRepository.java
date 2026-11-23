package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.InterviewResponse;

import java.util.Optional;

public interface InterviewResponseRepository extends JpaRepository<InterviewResponse, Integer> {
    Optional<InterviewResponse> findBySessionQuestionId(Integer sessionQuestionId);
}
