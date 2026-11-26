package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.MatchJdLink;
import recruit.demo.enums.SyncStatus;

import java.util.Collection;
import java.util.List;

public interface MatchJdLinkRepository extends JpaRepository<MatchJdLink, Integer> {
    List<MatchJdLink> findByStatusIn(Collection<SyncStatus> statuses);
}
