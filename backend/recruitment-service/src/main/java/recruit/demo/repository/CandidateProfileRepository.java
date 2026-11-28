package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.CandidateProfile;

import java.util.Optional;

public interface CandidateProfileRepository extends JpaRepository<CandidateProfile, Integer> {
    @org.springframework.data.jpa.repository.Modifying
    @org.springframework.data.jpa.repository.Query(value="INSERT IGNORE INTO candidate_profiles (user_id) VALUES (:userId)", nativeQuery=true)
    void insertIfAbsent(@org.springframework.data.repository.query.Param("userId") Integer userId);

    @org.springframework.data.jpa.repository.Query("""
        select candidate from CandidateProfile candidate
        where candidate.openForJob = true
            and exists (select flag.id from CvData flag where flag.candidateId = candidate.id
                and flag.field = 'parsing_status' and flag.value = 'COMPLETED')
            and (locate(lower(:query), lower(coalesce(candidate.headline, ''))) > 0
                or locate(lower(:query), lower(coalesce(candidate.summary, ''))) > 0
                or exists (select cv.id from CvData cv where cv.candidateId = candidate.id
                    and cv.field in ('Kỹ năng', 'Tóm tắt', 'Mô tả', 'Kinh nghiệm', 'Kỹ năng suy ra')
                    and locate(lower(:query), lower(cv.value)) > 0))
        order by candidate.id desc
        """)
    org.springframework.data.domain.Page<CandidateProfile> searchOpenCv(
        @org.springframework.data.repository.query.Param("query") String query,
        org.springframework.data.domain.Pageable pageable);

    @org.springframework.data.jpa.repository.Lock(jakarta.persistence.LockModeType.PESSIMISTIC_WRITE)
    @org.springframework.data.jpa.repository.Query("select c from CandidateProfile c where c.userId = :userId")
    Optional<CandidateProfile> lockByUserId(@org.springframework.data.repository.query.Param("userId") Integer userId);

    Optional<CandidateProfile> findByUserId(Integer userId);
}
