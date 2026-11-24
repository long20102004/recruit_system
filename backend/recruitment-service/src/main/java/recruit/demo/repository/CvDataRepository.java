package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.CvData;

import java.util.List;

public interface CvDataRepository extends JpaRepository<CvData, Integer> {
    List<CvData> findByCandidateId(Integer candidateId);

    List<CvData> findByCandidateIdAndFieldOrderByIdAsc(Integer candidateId, String field);
    List<CvData> findByFieldAndValue(String field, String value);
}
