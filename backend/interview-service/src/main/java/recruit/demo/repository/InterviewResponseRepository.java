package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.InterviewResponse;

import java.util.Optional;

public interface InterviewResponseRepository extends JpaRepository<InterviewResponse, Integer> {
    interface PendingEvaluation {
        Integer getResponseId();
        Integer getSessionId();
    }

    @org.springframework.data.jpa.repository.Query("""
        select r.id as responseId, r.sessionQuestion.session.id as sessionId
        from InterviewResponse r where r.status = 'PENDING' order by r.id
        """)
    java.util.List<PendingEvaluation> pending(org.springframework.data.domain.Pageable pageable);

    @org.springframework.data.jpa.repository.Modifying
    @org.springframework.transaction.annotation.Transactional
    @org.springframework.data.jpa.repository.Query(
        "update InterviewResponse r set r.status = 'FAILED' where r.id = :id and r.status = 'PENDING'")
    void failPending(@org.springframework.data.repository.query.Param("id") Integer id);

    Optional<InterviewResponse> findBySessionQuestionId(Integer sessionQuestionId);
}
