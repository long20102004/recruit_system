package recruit.demo.service;

import java.util.List;
import recruit.demo.dto.MatchingDtos;

public interface MatchingService {
    List<MatchingDtos.MatchResponse> myMatches();
    List<MatchingDtos.MatchResponse> refreshMine();
    List<MatchingDtos.MatchResponse> matchesForJob(Integer jobId);
    List<MatchingDtos.MatchResponse> refreshForJob(Integer jobId, String scope);
    MatchingDtos.ExplanationResponse explanation(Integer matchId);
    MatchingDtos.MatchResponse runMatching(MatchingDtos.RunMatchingRequest request);
}
