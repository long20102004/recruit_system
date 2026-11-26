package recruit.demo.service;

import recruit.demo.enums.Role;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.MatchingDtos;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.cvmatch.CvMatchMatching;

import java.util.List;

/**
 * Quyen va dieu phoi cho /api/matching. Viec match do module cvmatch (services/cvmatch-ai) lam qua {@link CvMatchMatching};
 * dich vu cv-matching-ai cu da go (dong cu trong matching_results giu engine = 'legacy', khong hien nua).
 */
@Service
@RequiredArgsConstructor
public class MatchingService {
    private final MatchingResultRepository matchingResultRepository;
    private final JobRepository jobRepository;
    private final CandidateProfileRepository candidateProfileRepository;
    private final CvDataRepository cvDataRepository;
    private final CvMatchMatching cvmatch;

    @Transactional(readOnly = true)
    public List<MatchingDtos.MatchResponse> myMatches() {
        SecurityUtils.requireRole(Role.CANDIDATE);
        CandidateProfile candidate = requireCandidate();
        if (!hasAnalyzedCv(candidate)) {
            return List.of();
        }
        return cvmatch.resultsForCandidate(candidate);
    }

    /** Luong D: mot lan goi cvmatch cho moi job dang mo. */
    @Transactional
    public List<MatchingDtos.MatchResponse> refreshMine() {
        SecurityUtils.requireRole(Role.CANDIDATE);
        CandidateProfile candidate = requireCandidate();
        requireAnalyzedCv(candidate);
        return cvmatch.refreshForCandidate(candidate);
    }

    @Transactional(readOnly = true)
    public List<MatchingDtos.MatchResponse> matchesForJob(Integer jobId) {
        SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
        Job job = requireJob(jobId);
        ensureRecruiterOwns(job);
        return cvmatch.resultsForJob(job);
    }

    /**
     * Recruiter chay lai xep hang ung vien cho job (Luong C). scope: applicants (mac dinh) = ung vien da nop don;
     * pool = ca kho CV (chi ADMIN).
     */
    @Transactional
    public List<MatchingDtos.MatchResponse> refreshForJob(Integer jobId, String scope) {
        SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
        Job job = requireJob(jobId);
        ensureRecruiterOwns(job);
        boolean pool = "pool".equalsIgnoreCase(scope);
        if (pool && SecurityUtils.currentUser().getRole() != Role.ADMIN) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Chỉ admin được xếp hạng toàn bộ kho CV");
        }
        return cvmatch.refreshForJob(job, pool);
    }

    /** Giai thich cua mot ket qua: ung vien xem ket qua cua minh, recruiter xem job cua minh. */
    @Transactional
    public MatchingDtos.ExplanationResponse explanation(Integer matchId) {
        MatchingResult m = matchingResultRepository.findById(matchId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Match not found"));
        if (!CvMatchMatching.ENGINE.equals(m.getEngine())) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Kết quả cũ không có giải thích chi tiết; hãy chạy lại ghép hồ sơ");
        }
        UserPrincipal principal = SecurityUtils.currentUser();
        if (principal.getRole() == Role.CANDIDATE) {
            CandidateProfile me = requireCandidate();
            if (!me.getId().equals(m.getCandidate().getId()) || !CvMatchMatching.TO_JD.equals(m.getDirection())) {
                throw new ApiException(HttpStatus.FORBIDDEN, "Not your match");
            }
        } else {
            SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
            ensureRecruiterOwns(m.getJob());
            if (!CvMatchMatching.TO_CV.equals(m.getDirection())) {
                throw new ApiException(HttpStatus.FORBIDDEN, "Kết quả này thuộc chiều ứng viên");
            }
        }
        return cvmatch.explanation(m);
    }

    /** Cham mot cap: ung vien voi mot job, hoac recruiter voi mot ung vien cua job minh. */
    @Transactional
    public MatchingDtos.MatchResponse runMatching(MatchingDtos.RunMatchingRequest request) {
        if (request == null || request.jobId() == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "jobId is required");
        }
        Job job = requireJob(request.jobId());
        UserPrincipal principal = SecurityUtils.currentUser();
        if (principal.getRole() == Role.CANDIDATE) {
            CandidateProfile candidate = requireCandidate();
            requireAnalyzedCv(candidate);
            return cvmatch.runForCandidate(candidate, job);
        }
        SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
        if (request.candidateId() == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "candidateId is required for recruiter matching");
        }
        ensureRecruiterOwns(job);
        CandidateProfile candidate = candidateProfileRepository.findById(request.candidateId())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Candidate not found"));
        return cvmatch.runForRecruiter(job, candidate);
    }

    private Job requireJob(Integer jobId) {
        return jobRepository.findById(jobId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
    }

    private void requireAnalyzedCv(CandidateProfile candidate) {
        if (!hasAnalyzedCv(candidate)) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Hãy tải CV để hệ thống phân tích và trích xuất dữ liệu trước khi xem việc phù hợp");
        }
    }

    private boolean hasAnalyzedCv(CandidateProfile candidate) {
        return "COMPLETED".equals(fieldValue(candidate.getId(), CvService.PARSING_STATUS))
                && !fieldValue(candidate.getId(), CvService.FILE_NAME).isBlank();
    }

    private String fieldValue(Integer candidateId, String field) {
        return cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field).stream()
                .map(row -> row.getValue() == null ? "" : row.getValue())
                .filter(value -> !value.isBlank())
                .findFirst()
                .orElse("");
    }

    private CandidateProfile requireCandidate() {
        UserPrincipal principal = SecurityUtils.currentUser();
        return candidateProfileRepository.findByUserId(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Candidate profile not found"));
    }

    private void ensureRecruiterOwns(Job job) {
        UserPrincipal principal = SecurityUtils.currentUser();
        if (principal.getRole() == Role.ADMIN) {
            return;
        }
        if (!job.getCreatedById().equals(principal.getId())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Not your job");
        }
    }
}
