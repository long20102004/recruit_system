package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import recruit.demo.exception.ApiException;
import recruit.demo.service.cvmatch.CvMatchSync;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Van hanh dong bo cvmatch. /internal/** can X-Service-Token (InternalAccessFilter), gateway chan prefix nay.
 * Dung lai cvmatch-db tu MySQL: POST /internal/cvmatch/backfill?scope=all|cv|jd (lan dau bat, doi CVMATCH_HMAC_KEY,
 * mat DB cvmatch).
 */
@RestController
@RequestMapping("/internal/cvmatch")
@RequiredArgsConstructor
public class InternalCvMatchController {
    private final CvMatchSync sync;

    @PostMapping("/backfill")
    public Map<String, Object> backfill(@RequestParam(defaultValue = "all") String scope,
                                        @RequestParam(defaultValue = "false") boolean runNow) {
        if (!Set.of("all", "cv", "jd").contains(scope)) throw new ApiException(HttpStatus.BAD_REQUEST, "scope: all | cv | jd");
        Map<String, Object> out = new LinkedHashMap<>(sync.backfill(scope));
        if (!sync.enabled()) {
            out.put("note", "dong bo dang tat (CVMATCH_SYNC_ENABLED=false): chi danh dau PENDING");
        } else if (runNow) {
            out.put("processed", sync.retryDue());
        }
        return out;
    }

    @PostMapping("/candidates/{candidateId}/sync")
    public Map<String, Object> syncCandidate(@PathVariable Integer candidateId) {
        return Map.of("candidateId", candidateId, "status", String.valueOf(sync.syncCandidate(candidateId)));
    }

    @PostMapping("/jobs/{jobId}/sync")
    public Map<String, Object> syncJob(@PathVariable Integer jobId) {
        return Map.of("jobId", jobId, "status", String.valueOf(sync.syncJob(jobId)));
    }
}
