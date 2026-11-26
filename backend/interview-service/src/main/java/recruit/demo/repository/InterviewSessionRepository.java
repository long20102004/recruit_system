package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.InterviewSession;
import recruit.demo.enums.SessionStatus;

import java.time.LocalDateTime;
import java.util.List;

public interface InterviewSessionRepository extends JpaRepository<InterviewSession, Integer> {
    List<InterviewSession> findByCandidateIdOrderByCreatedAtDesc(Integer candidateId);
    Page<InterviewSession> findByCandidateUserIdOrderByCreatedAtDesc(Integer userId, Pageable pageable);
    @org.springframework.data.jpa.repository.Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE)
    @org.springframework.data.jpa.repository.Query("select s from InterviewSession s where s.id = :id")
    java.util.Optional<InterviewSession> findForUpdate(@org.springframework.data.repository.query.Param("id") Integer id);

    long countByStatus(SessionStatus status);
    long countByRecruiterUserIdAndStatusAndCompletedAtAfter(Integer recruiterUserId, SessionStatus status, LocalDateTime since);
}
