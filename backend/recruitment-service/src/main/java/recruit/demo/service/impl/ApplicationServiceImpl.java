package recruit.demo.service.impl;

import recruit.demo.service.*;
import recruit.demo.enums.ApplicationStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.Role;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.ApplicationDtos;
import recruit.demo.dto.PageResponse;
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
    public PageResponse<ApplicationDtos.ApplicationResponse> myApplications(Pageable pageable) {
        CandidateProfile candidate = requireCandidate();
        Page<JobApplication> page = applicationRepository.findByCandidateIdOrderByAppliedAtDesc(candidate.getId(), pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
    }

    @Transactional(readOnly = true)
    public PageResponse<ApplicationDtos.ApplicationResponse> recruiterApplications(Pageable pageable) {
        UserPrincipal principal = SecurityUtils.currentUser();
        Page<JobApplication> page = applicationRepository.findForRecruiterUser(principal.getId(), pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
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
