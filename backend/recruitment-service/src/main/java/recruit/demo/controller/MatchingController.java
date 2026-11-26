package recruit.demo.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.MatchingDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.MatchingService;

import java.util.List;

@RestController
@RequestMapping("/api/matching")
@RequiredArgsConstructor
public class MatchingController {

    private final MatchingService matchingService;

    @GetMapping("/mine")
    @PreAuthorize("hasAuthority('matching:read-own')")
    public BaseResponse<PageResponse<MatchingDtos.MatchResponse>> myMatches(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(matchingService.myMatches(Paging.of(page, size)));
    }

    @PostMapping("/mine/refresh")
    @PreAuthorize("hasAuthority('matching:read-own')")
    public List<MatchingDtos.MatchResponse> refreshMine() {
        return matchingService.refreshMine();
    }

    @GetMapping("/jobs/{jobId}")
    @PreAuthorize("hasAnyAuthority('matching:run', 'matching:read-all')")
    public BaseResponse<PageResponse<MatchingDtos.MatchResponse>> matchesForJob(
            @PathVariable Integer jobId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(matchingService.matchesForJob(jobId, Paging.of(page, size)));
    }

    @PostMapping("/jobs/{jobId}/refresh")
    @PreAuthorize("hasAnyAuthority('matching:run', 'matching:run-pool')")
    public List<MatchingDtos.MatchResponse> refreshForJob(@PathVariable Integer jobId,
                                                          @RequestBody(required = false) MatchingDtos.RefreshJobRequest request) {
        return matchingService.refreshForJob(jobId, request == null ? null : request.scope());
    }

    @GetMapping("/{matchId}/explanation")
    @PreAuthorize("hasAnyAuthority('matching:read-own', 'matching:run', 'matching:read-all')")
    public MatchingDtos.ExplanationResponse explanation(@PathVariable Integer matchId) {
        return matchingService.explanation(matchId);
    }

    @PostMapping("/run")
    @PreAuthorize("hasAnyAuthority('matching:read-own', 'matching:run')")
    public MatchingDtos.MatchResponse run(@RequestBody MatchingDtos.RunMatchingRequest request) {
        return matchingService.runMatching(request);
    }
}
