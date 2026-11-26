package recruit.demo.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.User;
import recruit.demo.enums.UserStatus;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Integer> {
    Optional<User> findByEmailIgnoreCase(String email);
    boolean existsByEmailIgnoreCase(String email);

    /** Tìm theo email / họ tên (chứa, không phân biệt hoa thường) và trạng thái; tham số null = bỏ qua. */
    @Query("""
            SELECT u FROM User u
            WHERE (:q IS NULL OR LOWER(u.email) LIKE LOWER(CONCAT('%', :q, '%'))
                              OR LOWER(u.fullName) LIKE LOWER(CONCAT('%', :q, '%')))
              AND (:status IS NULL OR u.status = :status)
            """)
    Page<User> search(@Param("q") String q, @Param("status") UserStatus status, Pageable pageable);
}
