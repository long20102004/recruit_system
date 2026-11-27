package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import recruit.demo.entity.CvData;

import java.util.List;

public interface CvDataRepository extends JpaRepository<CvData, Integer> {

    /**
     * Các dòng của field trong <b>CV chính</b> của ứng viên. Matching, cvmatch, phỏng vấn đọc CV theo ứng viên qua
     * method này nên luôn dùng CV chính (specs/007-multi-cv FR-002).
     */
    @Query("select d from CvData d where d.candidateId = :candidateId and d.field = :field and d.cvId in "
            + "(select c.id from CvDocument c where c.candidateId = :candidateId and c.main = true) order by d.id")
    List<CvData> findByCandidateIdAndFieldOrderByIdAsc(@Param("candidateId") Integer candidateId,
                                                       @Param("field") String field);

    /** Dòng có field = value, chỉ trong các CV chính. */
    @Query("select d from CvData d where d.field = :field and d.value = :value and d.cvId in "
            + "(select c.id from CvDocument c where c.main = true)")
    List<CvData> findByFieldAndValue(@Param("field") String field, @Param("value") String value);

    List<CvData> findByCvIdAndFieldOrderByIdAsc(Integer cvId, String field);

    List<CvData> findByCvIdInAndField(List<Integer> cvIds, String field);

    List<CvData> findByCvId(Integer cvId);

    /** Mọi dòng của một field, kể cả CV không phải CV chính (dùng khi migrate file lên R2). */
    List<CvData> findAllByField(String field);
}
