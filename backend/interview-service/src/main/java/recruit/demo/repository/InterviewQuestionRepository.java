package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.InterviewQuestion;

import java.util.List;

public interface InterviewQuestionRepository extends JpaRepository<InterviewQuestion, Integer> {
    List<InterviewQuestion> findByActiveTrueOrderByIdAsc();
    Page<InterviewQuestion> findByActiveTrueOrderByIdAsc(Pageable pageable);
    long countByActiveTrue();
}
