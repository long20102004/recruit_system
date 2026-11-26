package recruit.demo.controller;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ServiceDtos.InterviewContext;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
@RestController
@RequiredArgsConstructor
public class InternalRecruitmentController {
    private final CandidateProfileRepository candidates;
    private final recruit.demo.client.IdentityClient identity;
    private final recruit.demo.service.ProfileProvisioningService profiles;
    private final JobRepository jobs;
    private final JobSkillRepository jobSkills;
    private final CvDataRepository cvData;
    private final JobApplicationRepository applications;
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
            lower.contains("senior") || lower.contains("middle") || lower.contains("lead") ? "Middle" : "Junior";
        return new InterviewContext(candidate.getId(), userId, jobId, title, applicationId,
            required, candidateSkills, level, job == null ? null : job.getCreatedById());
    }
}
