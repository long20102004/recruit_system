package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.RecruiterProfile;

import java.util.List;
import java.util.Optional;

public interface RecruiterProfileRepository extends JpaRepository<RecruiterProfile, Integer> {
    @org.springframework.data.jpa.repository.Modifying
    @org.springframework.data.jpa.repository.Query(value="INSERT IGNORE INTO recruiter_profiles (user_id, company_id, position) VALUES (:userId, :companyId, 'Nhà tuyển dụng')", nativeQuery=true)
    void insertIfAbsent(@org.springframework.data.repository.query.Param("userId") Integer userId,
        @org.springframework.data.repository.query.Param("companyId") Integer companyId);


    Optional<RecruiterProfile> findFirstByUserIdOrderByCreatedAtAsc(Integer userId);

    List<RecruiterProfile> findByUserId(Integer userId);

    List<RecruiterProfile> findByCompanyId(Integer companyId);

    @Query("""
            SELECT rp FROM RecruiterProfile rp
            JOIN FETCH rp.company
            WHERE rp.userId = :userId
            """)
    List<RecruiterProfile> findByUserIdWithCompany(@Param("userId") Integer userId);
}
