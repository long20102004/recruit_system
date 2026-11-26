package recruit.demo.service;

import java.util.List;
import org.springframework.data.domain.Pageable;
import recruit.demo.dto.MatchingDtos;
import recruit.demo.dto.PageResponse;

public interface MatchingService {
    PageResponse<MatchingDtos.MatchResponse> myMatches(Pageable pageable);
    List<MatchingDtos.MatchResponse> refreshMine();
    PageResponse<MatchingDtos.MatchResponse> matchesForJob(Integer jobId, Pageable pageable);
    List<MatchingDtos.MatchResponse> refreshForJob(Integer jobId, String scope);
    MatchingDtos.ExplanationResponse explanation(Integer matchId);
    MatchingDtos.MatchResponse runMatching(MatchingDtos.RunMatchingRequest request);
}
