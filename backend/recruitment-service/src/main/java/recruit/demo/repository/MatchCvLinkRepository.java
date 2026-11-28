package recruit.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import recruit.demo.entity.MatchCvLink;
import recruit.demo.enums.SyncStatus;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface MatchCvLinkRepository extends JpaRepository<MatchCvLink, Integer> {
    List<MatchCvLink> findByStatusIn(Collection<SyncStatus> statuses);

    @org.springframework.data.jpa.repository.Query("""
        select link from MatchCvLink link where link.status = :status and link.contentHash is not null
            and link.candidateId > :afterId
            and (link.suggestionCvHash is null or link.suggestionCvHash <> link.contentHash
                or link.suggestionCatalogHash is null or link.suggestionCatalogHash <> :catalogHash)
        order by link.candidateId
        """)
    List<MatchCvLink> staleSuggestions(@org.springframework.data.repository.query.Param("status") SyncStatus status,
        @org.springframework.data.repository.query.Param("catalogHash") String catalogHash,
        @org.springframework.data.repository.query.Param("afterId") Integer afterId,
        org.springframework.data.domain.Pageable pageable);

    @org.springframework.data.jpa.repository.Modifying
    @org.springframework.transaction.annotation.Transactional
    @org.springframework.data.jpa.repository.Query("""
        update MatchCvLink link set link.suggestionCvHash = :cvHash, link.suggestionCatalogHash = :catalogHash
        where link.candidateId = :candidateId and link.contentHash = :cvHash
        """)
    void recordSuggestionFingerprint(@org.springframework.data.repository.query.Param("candidateId") Integer candidateId,
        @org.springframework.data.repository.query.Param("cvHash") String cvHash,
        @org.springframework.data.repository.query.Param("catalogHash") String catalogHash);

    Optional<MatchCvLink> findByCvId(String cvId);

    List<MatchCvLink> findByCandidateIdIn(Collection<Integer> candidateIds);
}
