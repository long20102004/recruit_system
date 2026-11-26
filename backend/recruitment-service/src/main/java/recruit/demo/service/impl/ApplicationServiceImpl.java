package recruit.demo.service.impl;

import recruit.demo.service.*;
import recruit.demo.enums.ApplicationStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.Role;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.ApplicationDtos;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ApplicationServiceImpl implements ApplicationService {
    private final recruit.demo.client.IdentityClient identityClient;

    private final JobApplicationRepository applicationRepository;
    private final JobRepository jobRepository;
    private final CandidateProfileRepository candidateProfileRepository;

    @Transactional
    public ApplicationDtos.ApplicationResponse apply(Integer jobId, ApplicationDtos.ApplyRequest request) {
        SecurityUtils.requireRole(Role.CANDIDATE);
        CandidateProfile candidate = requireCandidate();
        Job job = jobRepository.findById(jobId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        if (job.getStatus() != JobStatus.PUBLISHED) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Job is not open for applications");
        }
        if (applicationRepository.findByJobIdAndCandidateId(jobId, candidate.getId()).isPresent()) {
            throw new ApiException(HttpStatus.CONFLICT, "Already applied to this job");
        }

        JobApplication application = JobApplication.builder()
                .job(job)
                .candidate(candidate)
                .status(ApplicationStatus.SUBMITTED)
                .coverLetter(request != null ? request.coverLetter() : null)
                .build();
        applicationRepository.save(application);
        return toResponse(application);
    }

    @Transactional(readOnly = true)
    public List<ApplicationDtos.ApplicationResponse> myApplications() {
        SecurityUtils.requireRole(Role.CANDIDATE);
        CandidateProfile candidate = requireCandidate();
        return applicationRepository.findByCandidateIdOrderByAppliedAtDesc(candidate.getId()).stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<ApplicationDtos.ApplicationResponse> recruiterApplications() {
        SecurityUtils.requireRole(Role.RECRUITER, Role.ADMIN);
        UserPrincipal principal = SecurityUtils.currentUser();
        return applicationRepository.findForRecruiterUser(principal.getId()).stream()
                .map(this::toResponse)
                .toList();
    }

    private ApplicationDtos.ApplicationResponse toResponse(JobApplication app) {
        return new ApplicationDtos.ApplicationResponse(
                app.getId(),
                app.getJob().getId(),
                app.getJob().getTitle(),
                app.getJob().getCompany().getName(),
                app.getCandidate().getId(),
                identityClient.get(app.getCandidate().getUserId()).fullName(),
                app.getCvId(),
                app.getStatus(),
                app.getCoverLetter(),
                app.getAppliedAt()
        );
    }

    private CandidateProfile requireCandidate() {
        UserPrincipal principal = SecurityUtils.currentUser();
        return candidateProfileRepository.findByUserId(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Candidate profile not found"));
    }
}
