package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.InterviewQuestion;

import java.util.List;

public interface InterviewQuestionRepository extends JpaRepository<InterviewQuestion, Integer> {
    Page<InterviewQuestion> findByArchivedFalseOrderByIdDesc(Pageable pageable);

    @org.springframework.data.jpa.repository.Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE)
    @org.springframework.data.jpa.repository.Query("select q from InterviewQuestion q where q.id = :id and q.archived = false")
    java.util.Optional<InterviewQuestion> findEditable(@org.springframework.data.repository.query.Param("id") Integer id);

    List<InterviewQuestion> findByActiveTrueOrderByIdAsc();
    Page<InterviewQuestion> findByActiveTrueOrderByIdAsc(Pageable pageable);
    long countByActiveTrue();
}
