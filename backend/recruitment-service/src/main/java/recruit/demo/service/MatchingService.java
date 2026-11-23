package recruit.demo.service;

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

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

@Service
@RequiredArgsConstructor
public class MatchingService {
    private final recruit.demo.client.IdentityClient identityClient;

    private static final String MODEL_NAME = "graph-semantic-matcher";
    private static final String MODEL_VERSION = "kb-graph-v1";

    private final MatchingResultRepository matchingResultRepository;
    private final JobRepository jobRepository;
    private final JobSkillRepository jobSkillRepository;
    private final CandidateProfileRepository candidateProfileRepository;
    private final CvDataRepository cvDataRepository;
    private final recruit.demo.service.matching.CvMatchingModule matchingModule;
    private final tools.jackson.databind.ObjectMapper objectMapper;

    @Transactional(readOnly = true)
    public List<MatchingDtos.MatchResponse> myMatches() {
        SecurityUtils.requireRole(Role.CANDIDATE);
        CandidateProfile candidate = requireCandidate();
        if (!hasAnalyzedCv(candidate)) {
            return List.of();
        }
        return matchingResultRepository.findByCandidateId(candidate.getId()).stream()
                .map(this::toResponse)
                .sorted(Comparator.comparing(MatchingDtos.MatchResponse::overallScore).reversed())
                .toList();
    }

    @Transactional
    public List<MatchingDtos.MatchResponse> refreshMine() {
        SecurityUtils.requireRole(Role.CANDIDATE);
        CandidateProfile candidate = requireCandidate();
        if (!hasAnalyzedCv(candidate)) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Hãy tải CV để hệ thống phân tích và trích xuất dữ liệu trước khi xem việc phù hợp");
        }
        List<MatchingDtos.MatchResponse> results = new ArrayList<>();
        for (Job job : jobRepository.search(null, null, JobStatus.PUBLISHED)) {
            results.add(runMatching(new MatchingDtos.RunMatchingRequest(job.getId(), null)));
        }
        results.sort(Comparator.comparing(MatchingDtos.MatchResponse::overallScore).reversed());
        return results;
    }

    @Transactional(readOnly = true)
    public List<MatchingDtos.MatchResponse> matchesForJob(Integer jobId) {
        SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
        Job job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        ensureRecruiterOwns(job);
        return matchingResultRepository.findByJobId(jobId).stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional
    public MatchingDtos.MatchResponse runMatching(MatchingDtos.RunMatchingRequest request) {
        if (request == null || request.jobId() == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "jobId is required");
        }
        Job job = jobRepository.findById(request.jobId())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));

        CandidateProfile candidate;
        UserPrincipal principal = SecurityUtils.currentUser();
        if (principal.getRole() == Role.CANDIDATE) {
            candidate = requireCandidate();
            if (!hasAnalyzedCv(candidate)) {
                throw new ApiException(
                        HttpStatus.BAD_REQUEST,
                        "Hãy tải CV để hệ thống phân tích và trích xuất dữ liệu trước khi xem việc phù hợp");
            }
        } else {
            SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
            if (request.candidateId() == null) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "candidateId is required for recruiter matching");
            }
            ensureRecruiterOwns(job);
            candidate = candidateProfileRepository.findById(request.candidateId())
                    .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Candidate not found"));
        }

        Set<String> candidateSkills = skillsOf(candidate);
        List<String> impliedSkills = skillsOfField(candidate, "Kỹ năng suy ra");

        List<JobSkill> jobSkills = jobSkillRepository.findByJobId(job.getId());
        List<String> required = jobSkills.stream().filter(JobSkill::isRequired)
                .map(js -> js.getSkill().getName()).toList();
        Map<String,Object> profile = new LinkedHashMap<>();
        String extracted = fieldValue(candidate.getId(), "extracted_profile");
        if (!extracted.isBlank()) {
            try { profile.putAll(objectMapper.readValue(extracted, Map.class)); }
            catch (Exception ex) { throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, "Stored CV profile is invalid; upload CV again"); }
        }
        profile.put("skills", new ArrayList<>(candidateSkills));
        profile.put("implied_skills", impliedSkills);
        profile.put("summary", fieldValue(candidate.getId(), "Tóm tắt"));
        // Confirmed form fields override the extraction, including corrections to jobs/education.
        profile.put("experience_text", allValues(candidate.getId(), "Kinh nghiệm"));
        profile.put("education_text", allValues(candidate.getId(), "Học vấn"));
        profile.put("certificates", allValues(candidate.getId(), "Chứng chỉ"));
        Map<String,Object> jd = new LinkedHashMap<>();
        jd.put("title", job.getTitle());
        jd.put("description", Objects.toString(job.getDescription(), "") + " " + Objects.toString(job.getRequirements(), ""));
        jd.put("required_skills", required);
        jd.put("min_experience_years", job.getExperienceRequired() == null ? 0 : job.getExperienceRequired());
        var ai = matchingModule.match(profile, jd);
        var feature = ai.path("feature_scores");
        BigDecimal skillsScore = BigDecimal.valueOf(feature.path("skill").asDouble()).setScale(4, RoundingMode.HALF_UP);
        BigDecimal experienceScore = BigDecimal.valueOf(feature.path("experience").asDouble()).setScale(4, RoundingMode.HALF_UP);
        BigDecimal semanticScore = BigDecimal.valueOf(feature.path("context").asDouble()).setScale(4, RoundingMode.HALF_UP);
        BigDecimal overall = BigDecimal.valueOf(ai.path("score").asDouble()).movePointLeft(2).setScale(4, RoundingMode.HALF_UP);
        List<String> matched = recruit.demo.service.cv.CvProfileMapper.strings(ai.path("matched_skills"));
        List<String> missing = recruit.demo.service.cv.CvProfileMapper.strings(ai.path("missing_skills"));
        String explanation = recruit.demo.service.cv.CvProfileMapper.text(ai.path("reasoning"));

        MatchingResult result = matchingResultRepository
                .findFirstByJobIdAndCandidateIdAndModelNameAndModelVersionOrderByCreatedAtDesc(
                        job.getId(), candidate.getId(), MODEL_NAME, MODEL_VERSION)
                .orElse(MatchingResult.builder()
                        .job(job)
                        .candidate(candidate)
                        .modelName(MODEL_NAME)
                        .modelVersion(MODEL_VERSION)
                        .build());

        result.setCvId(null);
        result.setOverallScore(overall);
        result.setSemanticScore(semanticScore);
        result.setSkillsScore(skillsScore);
        result.setExperienceScore(experienceScore);
        result.setMatchedSkills(List.copyOf(matched));
        result.setMissingSkills(List.copyOf(missing));
        result.setExplanation(explanation);
        matchingResultRepository.save(result);

        return toResponse(result);
    }

    private MatchingDtos.MatchResponse toResponse(MatchingResult m) {
        List<String> reasons = new ArrayList<>();
        if (m.getExplanation() != null && !m.getExplanation().isBlank()) {
            for (String part : m.getExplanation().split("\\.\\s*")) {
                if (!part.isBlank()) {
                    reasons.add(part.trim());
                }
            }
        }
        String modelVersionLabel = (m.getModelName() != null ? m.getModelName() : "")
                + (m.getModelVersion() != null ? "-" + m.getModelVersion() : "");

        return new MatchingDtos.MatchResponse(
                m.getId(),
                m.getJob().getId(),
                m.getJob().getTitle(),
                m.getJob().getCompany().getName(),
                m.getCandidate().getId(),
                identityClient.get(m.getCandidate().getUserId()).fullName(),
                m.getOverallScore(),
                m.getSemanticScore(),
                null,
                m.getSkillsScore(),
                m.getMatchedSkills() != null ? m.getMatchedSkills() : List.of(),
                m.getMissingSkills() != null ? m.getMissingSkills() : List.of(),
                reasons,
                modelVersionLabel.isBlank() ? m.getModelVersion() : modelVersionLabel,
                null,
                m.getCreatedAt()
        );
    }

    private boolean hasAnalyzedCv(CandidateProfile candidate) {
        return "COMPLETED".equals(fieldValue(candidate.getId(), CvService.PARSING_STATUS))
                && !fieldValue(candidate.getId(), CvService.FILE_NAME).isBlank();
    }

    private List<String> allValues(Integer candidateId, String field) {
        return cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field).stream()
            .map(CvData::getValue).filter(Objects::nonNull).toList();
    }

    private List<String> skillsOfField(CandidateProfile candidate, String field) {
        List<String> skills = new ArrayList<>();
        for (CvData row : cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidate.getId(), field)) {
            if (row.getValue() == null) {
                continue;
            }
            for (String part : row.getValue().split("[,;\\n]")) {
                if (!part.isBlank()) {
                    skills.add(part.trim());
                }
            }
        }
        return skills;
    }

    private Set<String> skillsOf(CandidateProfile candidate) {
        return new HashSet<>(skillsOfField(candidate, "Kỹ năng"));
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
