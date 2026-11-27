package recruit.demo.repository;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.EmailDeliveryEntity;
import recruit.demo.enums.EmailDeliveryStatus;

import java.time.Instant;
import java.util.List;

public interface EmailDeliveryRepository extends JpaRepository<EmailDeliveryEntity, Long> {

    boolean existsByEventIdAndUserId(String eventId, Integer userId);

    /** Email chờ gửi đã tới lượt thử (next_attempt_at null hoặc đã qua). */
    @Query("""
            SELECT d FROM EmailDeliveryEntity d
            WHERE d.status = :status AND d.attempts < :maxAttempts
              AND (d.nextAttemptAt IS NULL OR d.nextAttemptAt <= :now)
            ORDER BY d.id ASC
            """)
    List<EmailDeliveryEntity> findDue(@Param("status") EmailDeliveryStatus status,
                                      @Param("maxAttempts") int maxAttempts,
                                      @Param("now") Instant now,
                                      Pageable pageable);
}
