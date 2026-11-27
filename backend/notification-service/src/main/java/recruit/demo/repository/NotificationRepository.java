package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.NotificationEntity;

import java.time.Instant;
import java.util.Optional;

public interface NotificationRepository extends JpaRepository<NotificationEntity, Long> {

    boolean existsByEventIdAndUserId(String eventId, Integer userId);

    long countByUserIdAndReadAtIsNull(Integer userId);

    Optional<NotificationEntity> findByIdAndUserId(Long id, Integer userId);

    @Query("""
            SELECT n FROM NotificationEntity n
            WHERE n.userId = :userId
              AND (:category IS NULL OR n.category = :category)
              AND (:unreadOnly = false OR n.readAt IS NULL)
            ORDER BY n.createdAt DESC, n.id DESC
            """)
    Page<NotificationEntity> findUserNotifications(
            @Param("userId") Integer userId,
            @Param("category") String category,
            @Param("unreadOnly") boolean unreadOnly,
            Pageable pageable);

    @Modifying
    @Query("UPDATE NotificationEntity n SET n.readAt = :now WHERE n.userId = :userId AND n.readAt IS NULL")
    int markAllRead(@Param("userId") Integer userId, @Param("now") Instant now);
}
