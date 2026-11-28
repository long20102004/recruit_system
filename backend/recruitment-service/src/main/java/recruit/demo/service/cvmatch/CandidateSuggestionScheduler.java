package recruit.demo.service.cvmatch;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.SyncStatus;
import recruit.demo.repository.CandidateProfileRepository;
import recruit.demo.repository.MatchCvLinkRepository;
import recruit.demo.repository.MatchJdLinkRepository;
import tools.jackson.databind.ObjectMapper;

import java.util.Map;
import java.util.Objects;

@Component
@RequiredArgsConstructor
@Slf4j
public class CandidateSuggestionScheduler {
    private final CvMatchSync sync;
    private final CvMatchMatching matching;
    private final MatchCvLinkRepository cvLinks;
    private final MatchJdLinkRepository jdLinks;
    private final CandidateProfileRepository candidates;
    private final ObjectMapper mapper;
    private int afterId;

    @Value("${app.cvmatch.suggestions.enabled:true}")
    private boolean enabled;

    @Scheduled(fixedDelayString = "${app.cvmatch.suggestions.interval-ms:60000}",
        initialDelayString = "${app.cvmatch.suggestions.interval-ms:60000}")
    public void refreshChangedSuggestions() {
        if (!enabled || !sync.enabled()) return;
        var catalog = jdLinks.openCatalog(SyncStatus.SYNCED, JobStatus.PUBLISHED).stream()
            .map(link -> link.getJobId() + ":" + Objects.toString(link.getContentHash(), "")).toList();
        if (catalog.isEmpty()) return;
        String fingerprint = CvMatchPayloads.contentHash(mapper, Map.of("jobs", catalog));
        var stale = cvLinks.staleSuggestions(SyncStatus.SYNCED, fingerprint, afterId, PageRequest.of(0, 10));
        if (stale.isEmpty()) afterId = 0;
        for (var link : stale) {
            afterId = link.getCandidateId();
            try {
                var candidate = candidates.findById(link.getCandidateId()).orElse(null);
                if (candidate == null) continue;
                matching.refreshForCandidate(candidate);
                cvLinks.recordSuggestionFingerprint(link.getCandidateId(), link.getContentHash(), fingerprint);
            } catch (RuntimeException failure) {
                log.warn("Cannot refresh job suggestions for candidate {}: {}", link.getCandidateId(), failure.getMessage());
                return;
            }
        }
    }
}
