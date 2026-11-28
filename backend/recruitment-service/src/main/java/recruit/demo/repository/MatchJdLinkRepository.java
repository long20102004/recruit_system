package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.MatchJdLink;
import recruit.demo.enums.SyncStatus;

import java.util.Collection;
import java.util.List;

public interface MatchJdLinkRepository extends JpaRepository<MatchJdLink, Integer> {
    @org.springframework.data.jpa.repository.Query("""
        select link from MatchJdLink link join Job j on j.id = link.jobId
        where link.status = :status and j.status = :jobStatus
            and link.jdStatus = 'open' and (j.deadline is null or j.deadline > CURRENT_TIMESTAMP)
        order by link.jobId
        """)
    List<MatchJdLink> openCatalog(@org.springframework.data.repository.query.Param("status") SyncStatus status,
        @org.springframework.data.repository.query.Param("jobStatus") recruit.demo.enums.JobStatus jobStatus);

    @org.springframework.data.jpa.repository.Query("""
        select link from MatchJdLink link join Job j on j.id = link.jobId
        where link.status = :status and link.jdStatus = 'open'
            and j.deadline is not null and j.deadline <= CURRENT_TIMESTAMP
        order by j.deadline, j.id
        """)
    List<MatchJdLink> expiredCatalog(@org.springframework.data.repository.query.Param("status") SyncStatus status,
        org.springframework.data.domain.Pageable pageable);

    List<MatchJdLink> findByStatusIn(Collection<SyncStatus> statuses);
}
