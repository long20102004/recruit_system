package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.InterviewSessionQuestion;

import java.util.List;
import java.util.Optional;

public interface InterviewSessionQuestionRepository extends JpaRepository<InterviewSessionQuestion, Integer> {

    @Query("""
            SELECT sq FROM InterviewSessionQuestion sq
            JOIN FETCH sq.question
            WHERE sq.session.id = :sessionId
            ORDER BY sq.questionOrder ASC
            """)
    List<InterviewSessionQuestion> findBySessionIdOrdered(@Param("sessionId") Integer sessionId);

    @Query("select sq.question.id from InterviewSessionQuestion sq where sq.session.candidateUserId = :userId order by sq.session.createdAt desc, sq.questionOrder")
    List<Integer> recentQuestionIds(@Param("userId") Integer userId, org.springframework.data.domain.Pageable page);

    Optional<InterviewSessionQuestion> findBySessionIdAndQuestionId(Integer sessionId, Integer questionId);
}
