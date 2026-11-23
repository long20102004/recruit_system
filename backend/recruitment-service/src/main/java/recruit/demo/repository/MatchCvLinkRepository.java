package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.MatchCvLink;
import recruit.demo.entity.SyncStatus;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface MatchCvLinkRepository extends JpaRepository<MatchCvLink, Integer> {
    List<MatchCvLink> findByStatusIn(Collection<SyncStatus> statuses);

    Optional<MatchCvLink> findByCvId(String cvId);

    List<MatchCvLink> findByCandidateIdIn(Collection<Integer> candidateIds);
}
