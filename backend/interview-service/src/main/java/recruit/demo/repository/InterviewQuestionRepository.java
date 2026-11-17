package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.InterviewQuestion;

import java.util.List;

public interface InterviewQuestionRepository extends JpaRepository<InterviewQuestion, Integer> {
    List<InterviewQuestion> findByActiveTrueOrderByIdAsc();
    long countByActiveTrue();
}
