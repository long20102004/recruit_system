package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.MatchingDtos;
import recruit.demo.service.MatchingService;

import java.util.List;

@RestController
@RequestMapping("/api/matching")
@RequiredArgsConstructor
public class MatchingController {

    private final MatchingService matchingService;

    @GetMapping("/mine")
    public List<MatchingDtos.MatchResponse> myMatches() {
        return matchingService.myMatches();
    }

    @PostMapping("/mine/refresh")
    public List<MatchingDtos.MatchResponse> refreshMine() {
        return matchingService.refreshMine();
    }

    @GetMapping("/jobs/{jobId}")
    public List<MatchingDtos.MatchResponse> matchesForJob(@PathVariable Integer jobId) {
        return matchingService.matchesForJob(jobId);
    }

    @PostMapping("/jobs/{jobId}/refresh")
    public List<MatchingDtos.MatchResponse> refreshForJob(@PathVariable Integer jobId,
                                                          @RequestBody(required = false) MatchingDtos.RefreshJobRequest request) {
        return matchingService.refreshForJob(jobId, request == null ? null : request.scope());
    }

    @GetMapping("/{matchId}/explanation")
    public MatchingDtos.ExplanationResponse explanation(@PathVariable Integer matchId) {
        return matchingService.explanation(matchId);
    }

    @PostMapping("/run")
    public MatchingDtos.MatchResponse run(@RequestBody MatchingDtos.RunMatchingRequest request) {
        return matchingService.runMatching(request);
    }
}
