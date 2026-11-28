package recruit.demo.controller;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.entity.CandidateProfile;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.CandidateProfileRepository;
import recruit.demo.repository.CvDataRepository;
import recruit.demo.repository.RecruiterProfileRepository;
import recruit.demo.security.SecurityUtils;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;

@RestController
@RequestMapping("/api/cvs")
@RequiredArgsConstructor
public class CvDiscoveryController {
    private final CandidateProfileRepository candidates;
    private final RecruiterProfileRepository recruiters;
    private final CvDataRepository cvData;

    public record Visibility(@NotNull Boolean open) {}
    public record SearchResult(Integer id, BigDecimal yearsOfExperience, List<String> skills) {}

    @GetMapping("/visibility")
    @PreAuthorize("hasAuthority('cv:manage-own')")
    @Transactional(readOnly = true)
    public Visibility visibility() {
        return new Visibility(candidate().isOpenForJob());
    }

    @PutMapping("/visibility")
    @PreAuthorize("hasAuthority('cv:manage-own')")
    @Transactional
    public Visibility updateVisibility(@Valid @RequestBody Visibility input) {
        candidate().setOpenForJob(input.open());
        return input;
    }

    @GetMapping("/search")
    @PreAuthorize("hasRole('RECRUITER') and hasAuthority('job:read-own')")
    @Transactional(readOnly = true)
    public PageResponse<SearchResult> search(@RequestParam String q, @RequestParam(defaultValue = "0") int page) {
        if (recruiters.findFirstByUserIdOrderByCreatedAtAsc(SecurityUtils.currentUser().getId()).isEmpty()) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Company membership required");
        }
        String query = q.trim();
        if (query.length() < 2 || query.length() > 120) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Nhập từ 2 đến 120 ký tự để tìm CV");
        }
        return PageResponse.toPageResponse(candidates.searchOpenCv(query, Paging.of(page, 20)),
            profile -> new SearchResult(profile.getId(), profile.getYearsOfExperience(),
                cvData.findByCandidateIdAndFieldOrderByIdAsc(profile.getId(), "Kỹ năng").stream()
                    .filter(row -> row.getValue() != null)
                    .flatMap(row -> Arrays.stream(row.getValue().split("[,;\n]")))
                    .map(String::trim).filter(value -> !value.isBlank()).distinct().limit(20).toList()));
    }

    private CandidateProfile candidate() {
        return candidates.findByUserId(SecurityUtils.currentUser().getId())
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Candidate profile not found"));
    }
}
