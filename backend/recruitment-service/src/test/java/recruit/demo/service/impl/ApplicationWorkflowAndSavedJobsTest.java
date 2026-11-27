package recruit.demo.service.impl;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.client.IdentityClient;
import recruit.demo.entity.*;
import recruit.demo.enums.ApplicationStatus;
import recruit.demo.enums.NotificationType;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.messaging.NotificationConstants;
import recruit.demo.messaging.NotificationEvent;
import recruit.demo.messaging.OutboxWriter;
import recruit.demo.repository.*;
import recruit.demo.security.UserPrincipal;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class ApplicationWorkflowAndSavedJobsTest {

    private IdentityClient identityClient;
    private JobApplicationRepository appRepo;
    private JobRepository jobRepo;
    private CandidateProfileRepository candRepo;
    private ApplicationStatusHistoryRepository histRepo;
    private ApplicationNoteRepository noteRepo;
    private CvDataRepository cvDataRepo;
    private MatchingResultRepository matchRepo;
    private JobSkillRepository jobSkillRepo;
    private SavedJobRepository savedJobRepo;
    private CvDocumentRepository cvDocRepo;
    private OutboxWriter outbox;

    private ApplicationServiceImpl appService;
    private SavedJobServiceImpl savedJobService;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() {
        identityClient = mock(IdentityClient.class);
        appRepo = mock(JobApplicationRepository.class);
        jobRepo = mock(JobRepository.class);
        candRepo = mock(CandidateProfileRepository.class);
        histRepo = mock(ApplicationStatusHistoryRepository.class);
        noteRepo = mock(ApplicationNoteRepository.class);
        cvDataRepo = mock(CvDataRepository.class);
        matchRepo = mock(MatchingResultRepository.class);
        jobSkillRepo = mock(JobSkillRepository.class);
        savedJobRepo = mock(SavedJobRepository.class);
        cvDocRepo = mock(CvDocumentRepository.class);
        outbox = mock(OutboxWriter.class);
        ObjectProvider<OutboxWriter> outboxProvider = mock(ObjectProvider.class);
        when(outboxProvider.getIfAvailable()).thenReturn(outbox);

        appService = new ApplicationServiceImpl(identityClient, mock(recruit.demo.storage.StorageService.class), appRepo, jobRepo, candRepo, histRepo,
                noteRepo, cvDataRepo, matchRepo, jobSkillRepo, new ObjectMapper(), cvDocRepo, outboxProvider);
        savedJobService = new SavedJobServiceImpl(savedJobRepo, jobRepo, candRepo, jobSkillRepo, matchRepo);

        when(appRepo.save(any(JobApplication.class))).thenAnswer(i -> i.getArgument(0));
        when(noteRepo.save(any(ApplicationNote.class))).thenAnswer(i -> i.getArgument(0));
        when(savedJobRepo.save(any(SavedJob.class))).thenAnswer(i -> i.getArgument(0));
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

    private Job openJob() {
        Company co = Company.builder().id(1).name("Lumen").build();
        return Job.builder().id(5).company(co).createdById(10).title("Java")
                .status(recruit.demo.enums.JobStatus.PUBLISHED).build();
    }

    @Test
    void applyWithoutCvUsesMainCv() {
        loginAs(70, Role.CANDIDATE);
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        when(candRepo.findByUserId(70)).thenReturn(Optional.of(cand));
        when(jobRepo.findById(5)).thenReturn(Optional.of(openJob()));
        when(cvDocRepo.findFirstByCandidateIdAndMainTrue(7))
                .thenReturn(Optional.of(CvDocument.builder().id(31).candidateId(7).main(true).build()));

        assertEquals(31, appService.apply(5, new recruit.demo.dto.ApplicationDtos.ApplyRequest(null, null)).cvDocumentId());
    }

    @Test
    void applyRejectsCvOfAnotherCandidate() {
        loginAs(70, Role.CANDIDATE);
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        when(candRepo.findByUserId(70)).thenReturn(Optional.of(cand));
        when(jobRepo.findById(5)).thenReturn(Optional.of(openJob()));
        when(cvDocRepo.findByIdAndCandidateId(99, 7)).thenReturn(Optional.empty());

        assertEquals(HttpStatus.BAD_REQUEST, assertThrows(ApiException.class,
                () -> appService.apply(5, new recruit.demo.dto.ApplicationDtos.ApplyRequest(99, null))).getStatus());
        verify(appRepo, never()).save(any(JobApplication.class));
    }

    @Test
    void applyWithSelectedAnalyzedCvStoresIt() {
        loginAs(70, Role.CANDIDATE);
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        when(candRepo.findByUserId(70)).thenReturn(Optional.of(cand));
        when(jobRepo.findById(5)).thenReturn(Optional.of(openJob()));
        when(cvDocRepo.findByIdAndCandidateId(32, 7))
                .thenReturn(Optional.of(CvDocument.builder().id(32).candidateId(7).build()));
        when(cvDataRepo.findByCvIdAndFieldOrderByIdAsc(32, "parsing_status"))
                .thenReturn(List.of(CvData.builder().cvId(32).candidateId(7).field("parsing_status").value("COMPLETED").build()));

        assertEquals(32, appService.apply(5, new recruit.demo.dto.ApplicationDtos.ApplyRequest(32, null)).cvDocumentId());
    }

    @Test
    void interviewStatusCanOnlyTransitionToHiredOrRejected() {
        loginAs(10, Role.RECRUITER);
        Company co = Company.builder().id(1).name("Lumen").build();
        Job job = Job.builder().id(5).company(co).createdById(10).title("Java").build();
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        JobApplication app = JobApplication.builder().id(99).job(job).candidate(cand).status(ApplicationStatus.INTERVIEW).build();
        when(appRepo.findById(99)).thenReturn(Optional.of(app));

        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> appService.updateStatus(99, "REVIEWING", "")).getStatus());

        var res = appService.updateStatus(99, "HIRED", "Great!");
        assertEquals(ApplicationStatus.HIRED, res.status());
        verify(histRepo).save(any(ApplicationStatusHistory.class));
    }

    @Test
    void candidateCanWithdrawSubmittedButNotHired() {
        loginAs(70, Role.CANDIDATE);
        Company co = Company.builder().id(1).name("Lumen").build();
        Job job = Job.builder().id(5).company(co).createdById(10).title("Java").build();
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        when(candRepo.findByUserId(70)).thenReturn(Optional.of(cand));

        JobApplication app = JobApplication.builder().id(99).job(job).candidate(cand).status(ApplicationStatus.SUBMITTED).build();
        when(appRepo.findById(99)).thenReturn(Optional.of(app));
        assertEquals(ApplicationStatus.WITHDRAWN, appService.withdraw(99).status());

        app.setStatus(ApplicationStatus.HIRED);
        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> appService.withdraw(99)).getStatus());
    }

    @Test
    void saveNoteValidatesRatingAndPersists() {
        loginAs(10, Role.RECRUITER);
        Company co = Company.builder().id(1).name("Lumen").build();
        Job job = Job.builder().id(5).company(co).createdById(10).title("Java").build();
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        JobApplication app = JobApplication.builder().id(99).job(job).candidate(cand).status(ApplicationStatus.REVIEWING).build();
        when(appRepo.findById(99)).thenReturn(Optional.of(app));

        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> appService.saveNote(99, 6, "Invalid")).getStatus());

        var detail = appService.saveNote(99, 4, "Strong Spring Boot");
        assertEquals(4, detail.rating());
        assertEquals("Strong Spring Boot", detail.internalNote());
    }

    @Test
    void savedJobSaveAndUnsaveByJobId() {
        loginAs(70, Role.CANDIDATE);
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        when(candRepo.findByUserId(70)).thenReturn(Optional.of(cand));
        Company co = Company.builder().id(1).name("Lumen").build();
        Job job = Job.builder().id(5).company(co).createdById(10).title("Java")
                .salaryMin(BigDecimal.valueOf(20_000_000)).build();
        when(jobRepo.findById(5)).thenReturn(Optional.of(job));
        when(jobSkillRepo.findByJobId(5)).thenReturn(List.of());

        SavedJob saved = SavedJob.builder().id(11).candidate(cand).job(job).build();
        when(savedJobRepo.findByCandidateIdAndJobId(7, 5)).thenReturn(Optional.empty()).thenReturn(Optional.of(saved));

        var dto = savedJobService.save(5);
        assertEquals(5, dto.jobId());
        savedJobService.unsave(5);
        verify(savedJobRepo).delete(saved);
    }

    @Test
    void transitionStatusEmitsInterviewInviteAndApplicationStatusEvents() {
        loginAs(10, Role.RECRUITER);
        Company co = Company.builder().id(1).name("Lumen").build();
        Job job = Job.builder().id(5).company(co).createdById(10).title("Java").build();
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        JobApplication app = JobApplication.builder().id(99).job(job).candidate(cand).status(ApplicationStatus.SUBMITTED).build();
        when(appRepo.findById(99)).thenReturn(Optional.of(app));

        appService.updateStatus(99, "INTERVIEW", "Meet team");
        ArgumentCaptor<NotificationEvent> captor = ArgumentCaptor.forClass(NotificationEvent.class);
        verify(outbox).add(eq(NotificationConstants.RK_APPLICATION_STATUS_CHANGED), captor.capture());
        NotificationEvent interviewEvent = captor.getValue();
        assertEquals(NotificationType.INTERVIEW_INVITE, interviewEvent.getType());
        assertEquals(List.of(70), interviewEvent.getRecipientUserIds());
        assertEquals("Lời mời phỏng vấn", interviewEvent.getTitle());
        assertEquals("Java · Lumen", interviewEvent.getBody());
        assertEquals("/candidate/applications", interviewEvent.getLink());
        assertEquals(99, interviewEvent.getData().get("applicationId"));
        assertEquals("INTERVIEW", interviewEvent.getData().get("status"));

        reset(outbox);
        appService.updateStatus(99, "HIRED", "Welcome");
        verify(outbox).add(eq(NotificationConstants.RK_APPLICATION_STATUS_CHANGED), captor.capture());
        NotificationEvent hiredEvent = captor.getValue();
        assertEquals(NotificationType.APPLICATION_STATUS, hiredEvent.getType());
        assertEquals("Đơn ứng tuyển Trúng tuyển", hiredEvent.getTitle());
        assertEquals("HIRED", hiredEvent.getData().get("status"));
    }

    @Test
    void invalidTransitionDoesNotEmitOutboxEvent() {
        loginAs(10, Role.RECRUITER);
        Company co = Company.builder().id(1).name("Lumen").build();
        Job job = Job.builder().id(5).company(co).createdById(10).title("Java").build();
        CandidateProfile cand = CandidateProfile.builder().id(7).userId(70).build();
        JobApplication app = JobApplication.builder().id(99).job(job).candidate(cand).status(ApplicationStatus.HIRED).build();
        when(appRepo.findById(99)).thenReturn(Optional.of(app));

        assertThrows(ApiException.class, () -> appService.updateStatus(99, "REJECTED", ""));
        verifyNoInteractions(outbox);
    }
}
