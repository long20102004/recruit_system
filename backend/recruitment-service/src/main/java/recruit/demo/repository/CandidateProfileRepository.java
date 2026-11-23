package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.CandidateProfile;

import java.util.Optional;

public interface CandidateProfileRepository extends JpaRepository<CandidateProfile, Integer> {
    @org.springframework.data.jpa.repository.Modifying
    @org.springframework.data.jpa.repository.Query(value="INSERT IGNORE INTO candidate_profiles (user_id) VALUES (:userId)", nativeQuery=true)
    void insertIfAbsent(@org.springframework.data.repository.query.Param("userId") Integer userId);

    Optional<CandidateProfile> findByUserId(Integer userId);
}
