package recruit.demo.service.impl;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.SavedJobDtos.SavedJobResponse;
import recruit.demo.entity.*;
import recruit.demo.enums.JobStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.SavedJobService;

import java.math.BigDecimal;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;

@Service
@RequiredArgsConstructor
public class SavedJobServiceImpl implements SavedJobService {

    private final SavedJobRepository savedJobRepository;
    private final JobRepository jobRepository;
    private final CandidateProfileRepository candidateProfileRepository;
    private final JobSkillRepository jobSkillRepository;
    private final MatchingResultRepository matchingResultRepository;

    @Override
    @Transactional(readOnly = true)
    public List<SavedJobResponse> listMine() {
        CandidateProfile candidate = requireCandidate();
        return savedJobRepository.findByCandidateIdOrderBySavedAtDesc(candidate.getId())
                .stream()
                .map(s -> toResponse(s, candidate.getId()))
                .toList();
    }

    @Override
    @Transactional
    public SavedJobResponse save(Integer jobId) {
        CandidateProfile candidate = requireCandidate();
        Job job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));

        SavedJob saved = savedJobRepository.findByCandidateIdAndJobId(candidate.getId(), jobId)
                .orElseGet(() -> savedJobRepository.save(SavedJob.builder()
                        .candidate(candidate)
                        .job(job)
                        .build()));
        return toResponse(saved, candidate.getId());
    }

    @Override
    @Transactional
    public void unsave(Integer jobIdOrSavedId) {
        CandidateProfile candidate = requireCandidate();
        var byJob = savedJobRepository.findByCandidateIdAndJobId(candidate.getId(), jobIdOrSavedId);
        if (byJob.isPresent()) {
            savedJobRepository.delete(byJob.get());
            return;
        }
        var byId = savedJobRepository.findById(jobIdOrSavedId)
                .filter(s -> s.getCandidate().getId().equals(candidate.getId()))
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy việc làm đã lưu."));
        savedJobRepository.delete(byId);
    }

    private SavedJobResponse toResponse(SavedJob saved, Integer candidateId) {
        Job job = saved.getJob();
        String companyName = job.getCompany().getName();
        List<String> skills = jobSkillRepository.findByJobId(job.getId()).stream()
                .map(js -> js.getSkill().getName())
                .limit(5)
                .toList();

        Integer matchPct = matchingResultRepository.findFirstByJobIdAndCandidateIdOrderByCreatedAtDesc(job.getId(), candidateId)
                .map(m -> m.getOverallScore() != null
                        ? Math.round(m.getOverallScore().multiply(BigDecimal.valueOf(100)).floatValue())
                        : null)
                .orElse(null);

        String uiStatus = switch (job.getStatus()) {
            case PUBLISHED -> "OPEN";
            case EXPIRED -> "EXPIRED";
            default -> "CLOSED";
        };
        boolean hot = job.isHot() || (job.getPostedAt() != null && job.getPostedAt().isAfter(LocalDateTime.now().minusDays(1)));

        return new SavedJobResponse(
                saved.getId(),
                job.getId(),
                job.getTitle(),
                companyName,
                initials(companyName),
                deriveCity(job.getWorkLocation()),
                job.getEmploymentType() != null ? job.getEmploymentType() : "Hybrid",
                job.getLevel() != null ? job.getLevel() : deriveLevel(job.getTitle()),
                formatSalary(job),
                skills,
                saved.getSavedAt(),
                job.getDeadline(),
                uiStatus,
                hot,
                matchPct
        );
    }

    private CandidateProfile requireCandidate() {
        UserPrincipal principal = SecurityUtils.currentUser();
        return candidateProfileRepository.findByUserId(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Candidate profile not found"));
    }

    private String formatSalary(Job job) {
        if (job.getSalaryMin() == null && job.getSalaryMax() == null) {
            return "Thỏa thuận";
        }
        DecimalFormat df = new DecimalFormat("#,###", new DecimalFormatSymbols(Locale.US));
        String currency = job.getCurrency() != null ? job.getCurrency() : "VND";
        if (job.getSalaryMin() != null && job.getSalaryMax() != null) {
            return df.format(job.getSalaryMin()) + " – " + df.format(job.getSalaryMax()) + " " + currency;
        }
        if (job.getSalaryMin() != null) {
            return "Từ " + df.format(job.getSalaryMin()) + " " + currency;
        }
        return "Đến " + df.format(job.getSalaryMax()) + " " + currency;
    }

    private String deriveCity(String loc) {
        if (loc == null || loc.isBlank()) return "Toàn quốc";
        String l = loc.toLowerCase(Locale.ROOT);
        if (l.contains("hà nội") || l.contains("ha noi")) return "Hà Nội";
        if (l.contains("hồ chí minh") || l.contains("hcm")) return "TP. Hồ Chí Minh";
        if (l.contains("đà nẵng") || l.contains("da nang")) return "Đà Nẵng";
        if (l.contains("remote")) return "Remote";
        return loc;
    }

    private String deriveLevel(String title) {
        if (title == null) return "Middle";
        String t = title.toLowerCase(Locale.ROOT);
        if (t.contains("intern") || t.contains("thực tập")) return "Intern";
        if (t.contains("junior") || t.contains("fresher")) return "Junior";
        if (t.contains("senior") || t.contains("lead")) return "Senior";
        return "Middle";
    }

    private String initials(String name) {
        if (name == null || name.isBlank()) return "CT";
        String[] p = name.trim().split("\\s+");
        if (p.length == 1) return p[0].substring(0, Math.min(2, p[0].length())).toUpperCase(Locale.ROOT);
        return (p[0].substring(0, 1) + p[p.length - 1].substring(0, 1)).toUpperCase(Locale.ROOT);
    }
}
