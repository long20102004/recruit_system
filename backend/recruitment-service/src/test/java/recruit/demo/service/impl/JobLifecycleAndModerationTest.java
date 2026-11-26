package recruit.demo.service.impl;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.JobDtos.CreateJobRequest;
import recruit.demo.entity.Company;
import recruit.demo.entity.Job;
import recruit.demo.entity.RecruiterProfile;
import recruit.demo.enums.CompanyStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.cvmatch.CvMatchEvents;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class JobLifecycleAndModerationTest {

    private JobRepository jobRepo;
    private JobSkillRepository jobSkillRepo;
    private SkillRepository skillRepo;
    private RecruiterProfileRepository recruiterRepo;
    private JobApplicationRepository appRepo;
    private IdentityClient identityClient;
    private ApplicationEventPublisher events;
    private JobServiceImpl service;
    private JobExpirationScheduler scheduler;

    @BeforeEach
    void setUp() {
        jobRepo = mock(JobRepository.class);
        jobSkillRepo = mock(JobSkillRepository.class);
        skillRepo = mock(SkillRepository.class);
        recruiterRepo = mock(RecruiterProfileRepository.class);
        appRepo = mock(JobApplicationRepository.class);
        identityClient = mock(IdentityClient.class);
        events = mock(ApplicationEventPublisher.class);
        service = new JobServiceImpl(jobRepo, jobSkillRepo, skillRepo, recruiterRepo, appRepo, identityClient, events);
        scheduler = new JobExpirationScheduler(jobRepo, events);
        when(jobRepo.save(any(Job.class))).thenAnswer(i -> {
            Job j = i.getArgument(0);
            if (j.getId() == null) j.setId(100);
            return j;
        });
    }

    @AfterEach
    void clear() {
        SecurityContextHolder.clearContext();
    }

    private void loginAs(int id, Role role) {
        var p = new UserPrincipal(id, "u" + id + "@x.test", "", "User " + id, role, UserStatus.ACTIVE);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(p, null, p.getAuthorities()));
    }

    @Test
    void cannotPublishWhenCompanyIsPending() {
        loginAs(10, Role.RECRUITER);
        Company pending = Company.builder().id(1).name("Pending Co").status(CompanyStatus.PENDING).build();
        when(recruiterRepo.findFirstByUserIdOrderByCreatedAtAsc(10))
                .thenReturn(Optional.of(RecruiterProfile.builder().id(1).userId(10).company(pending).build()));

        CreateJobRequest pubReq = new CreateJobRequest("Java Dev", "Desc", "HCM", "HCM", "Hybrid",
                "Junior", null, BigDecimal.ONE, false, JobStatus.PUBLISHED, List.of(), List.of());
        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.create(pubReq)).getStatus());

        CreateJobRequest draftReq = new CreateJobRequest("Java Dev", "Desc", "HCM", "HCM", "Hybrid",
                "Junior", null, BigDecimal.ONE, false, JobStatus.DRAFT, List.of(), List.of());
        assertEquals(JobStatus.DRAFT, service.create(draftReq).status());
    }

    @Test
    void deleteOnlyAllowedForDraftWithoutApplications() {
        loginAs(10, Role.RECRUITER);
        Company active = Company.builder().id(1).name("Co").status(CompanyStatus.ACTIVE).build();
        Job published = Job.builder().id(5).company(active).createdById(10).title("Dev").status(JobStatus.PUBLISHED).build();
        when(jobRepo.findById(5)).thenReturn(Optional.of(published));
        assertThrows(ApiException.class, () -> service.delete(5));

        Job draftWithApps = Job.builder().id(6).company(active).createdById(10).title("Dev").status(JobStatus.DRAFT).build();
        when(jobRepo.findById(6)).thenReturn(Optional.of(draftWithApps));
        when(appRepo.countByJobId(6)).thenReturn(2L);
        assertThrows(ApiException.class, () -> service.delete(6));

        when(appRepo.countByJobId(6)).thenReturn(0L);
        service.delete(6);
        verify(jobRepo).delete(draftWithApps);
    }

    @Test
    void schedulerMarksOverduePublishedJobsExpiredAndPublishesEvent() {
        Company active = Company.builder().id(1).name("Co").status(CompanyStatus.ACTIVE).build();
        Job overdue = Job.builder().id(77).company(active).createdById(10).title("Old")
                .status(JobStatus.PUBLISHED).deadline(LocalDateTime.now().minusDays(1)).build();
        when(jobRepo.findByStatusAndDeadlineBefore(eq(JobStatus.PUBLISHED), any())).thenReturn(List.of(overdue));

        scheduler.expireOverdueJobs();
        assertEquals(JobStatus.EXPIRED, overdue.getStatus());
        verify(events).publishEvent(any(CvMatchEvents.JobChanged.class));
    }

    @Test
    void adminLockAndUnlockRestoresCorrectStatus() {
        loginAs(1, Role.ADMIN);
        Company active = Company.builder().id(1).name("Co").status(CompanyStatus.ACTIVE).build();
        Job job = Job.builder().id(88).company(active).createdById(10).title("Backend")
                .status(JobStatus.PUBLISHED).deadline(LocalDateTime.now().plusDays(10)).build();
        when(jobRepo.findById(88)).thenReturn(Optional.of(job));

        var locked = service.lockJob(88, "Spam", "Fake");
        assertTrue(locked.locked());
        assertEquals(JobStatus.LOCKED, job.getStatus());
        verify(identityClient).recordAuditLog(eq("LOCK_JOB"), eq("Khoá tin"), any(), eq("Backend"), eq(1), any());

        service.unlockJob(88);
        assertEquals(JobStatus.PUBLISHED, job.getStatus());
        assertNull(job.getLockReason());
        verify(identityClient).recordAuditLog(eq("UNLOCK_JOB"), eq("Mở khoá tin"), any(), eq("Backend"), eq(1), any());
    }
}
