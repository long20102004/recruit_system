package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.CvDocument;

import java.util.List;
import java.util.Optional;

public interface CvDocumentRepository extends JpaRepository<CvDocument, Integer> {
    List<CvDocument> findByCandidateIdOrderByMainDescUpdatedAtDesc(Integer candidateId);

    Optional<CvDocument> findByIdAndCandidateId(Integer id, Integer candidateId);

    Optional<CvDocument> findFirstByCandidateIdAndMainTrue(Integer candidateId);

    long countByCandidateId(Integer candidateId);
}
