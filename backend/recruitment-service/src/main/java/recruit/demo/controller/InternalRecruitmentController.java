package recruit.demo.controller;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ServiceDtos.InterviewContext;
import recruit.demo.dto.ServiceDtos.RecruitmentAdminStats;
import recruit.demo.enums.CompanyStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import java.time.LocalDateTime;
@RestController
@RequiredArgsConstructor
public class InternalRecruitmentController {
    private final CandidateProfileRepository candidates;
    private final recruit.demo.client.IdentityClient identity;
    private final recruit.demo.service.ProfileProvisioningService profiles;
    private final JobRepository jobs;
    private final CompanyRepository companies;
    private final JobSkillRepository jobSkills;
    private final CvDataRepository cvData;
    private final JobApplicationRepository applications;
    private final RecruiterProfileRepository recruiters;

    @PostMapping("/internal/interview-results")
    @Transactional
    public void saveInterviewResult(@RequestBody recruit.demo.dto.ServiceDtos.CompletedInterview result) {
        var application = applications.findForUpdate(result.applicationId()).orElse(null);
        if (application == null || !application.getJob().getId().equals(result.jobId())
                || !application.getCandidate().getUserId().equals(result.candidateUserId())) return;

        var previous = application.getInterviewCompletedAt();
        if (previous != null && (previous.isAfter(result.completedAt())
                || (previous.equals(result.completedAt()) && application.getInterviewSessionId() != null
                && application.getInterviewSessionId() >= result.sessionId()))) return;

        application.setInterviewScore(result.averageScore());
        application.setInterviewCompletedAt(result.completedAt());
        application.setInterviewSessionId(result.sessionId());
    }

    @GetMapping("/internal/interview-access")
    @Transactional(readOnly = true)
    public boolean canReadInterview(@RequestParam Integer userId, @RequestParam Integer jobId) {
        return jobs.findById(jobId)
            .filter(job -> userId.equals(job.getCreatedById()))
            .map(job -> recruiters.existsByUserIdAndCompanyId(userId, job.getCompany().getId()))
            .orElse(false);
    }

    @GetMapping("/internal/interview-eligibility")
    @Transactional(readOnly = true)
    public boolean interviewEligible(@RequestParam Integer userId, @RequestParam Integer applicationId) {
        return applications.findById(applicationId)
            .filter(application -> userId.equals(application.getCandidate().getUserId()))
            .map(this::interviewEligible)
            .orElse(false);
    }

    private boolean interviewEligible(recruit.demo.entity.JobApplication application) {
        return application.getStatus() == recruit.demo.enums.ApplicationStatus.INTERVIEW
            && application.getJob().isOpenForApplications();
    }

    @GetMapping("/internal/stats/admin")
    @Transactional(readOnly = true)
    public RecruitmentAdminStats adminStats() {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime d30 = now.minusDays(30);
        LocalDateTime d60 = now.minusDays(60);
        return new RecruitmentAdminStats(
                companies.countByStatus(CompanyStatus.ACTIVE),
                companies.countByStatus(CompanyStatus.PENDING),
                jobs.countByStatus(JobStatus.PUBLISHED),
                jobs.countByStatus(JobStatus.LOCKED),
                applications.countByAppliedAtBetween(d30, now),
                applications.countByAppliedAtBetween(d60, d30)
        );
    }
    @GetMapping("/internal/interview-context")
    @Transactional
    public InterviewContext context(@RequestParam Integer userId,
            @RequestParam(required=false) Integer jobId, @RequestParam(required=false) Integer applicationId) {
        var user = identity.get(userId);
        if (user.role() != recruit.demo.enums.Role.CANDIDATE || user.status() != recruit.demo.enums.UserStatus.ACTIVE)
            throw new ApiException(HttpStatus.FORBIDDEN, "Active candidate required");
        profiles.ensureProfile(new recruit.demo.security.UserPrincipal(user.id(), user.email(), "", user.fullName(), user.role(), user.status()));
        var candidate = candidates.findByUserId(userId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Candidate profile not found; open your CV first"));
        if (applicationId != null) {
            var application = applications.findById(applicationId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Application not found"));
            if (!application.getCandidate().getId().equals(candidate.getId()))
                throw new ApiException(HttpStatus.FORBIDDEN, "Not your application");
            if (jobId != null && !jobId.equals(application.getJob().getId()))
                throw new ApiException(HttpStatus.BAD_REQUEST, "Application and job do not match");
            if (!interviewEligible(application))
                throw new ApiException(HttpStatus.CONFLICT, "Interview invitation is no longer active");
            jobId = application.getJob().getId();
        }
        var job = jobId == null ? null : jobs.findById(jobId)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        String title = job == null ? null : job.getTitle();
        var required = job == null ? java.util.List.<String>of() : jobSkills.findByJobId(job.getId()).stream()
            .filter(recruit.demo.entity.JobSkill::isRequired).map(js -> js.getSkill().getName()).toList();
        var candidateSkills = java.util.stream.Stream.of("Kỹ năng", "Kỹ năng suy ra")
            .flatMap(field -> cvData.findByCandidateIdAndFieldOrderByIdAsc(candidate.getId(), field).stream())
            .filter(row -> row.getValue() != null).flatMap(row -> java.util.Arrays.stream(row.getValue().split("[,;\\n]")))
            .map(String::trim).filter(value -> !value.isBlank()).distinct().toList();
        String lower = title == null ? "" : title.toLowerCase(java.util.Locale.ROOT);
        String level = lower.contains("intern") || lower.contains("fresher") ? "Intern" :
            lower.contains("senior") || lower.contains("lead") ? "Senior" :
            lower.contains("middle") || lower.contains("mid-level") ? "Middle" : "Junior";
        return new InterviewContext(candidate.getId(), userId, jobId, title, applicationId,
            required, candidateSkills, level, job == null ? null : job.getCreatedById());
    }
}
