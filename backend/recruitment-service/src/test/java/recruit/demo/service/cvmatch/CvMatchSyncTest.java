package recruit.demo.service.cvmatch;

import recruit.demo.enums.JobStatus;
import recruit.demo.enums.Role;
import recruit.demo.enums.SyncStatus;
import recruit.demo.enums.UserStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.SimpleTransactionStatus;
import recruit.demo.client.CvMatchApi;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.ServiceDtos;
import recruit.demo.entity.*;
import recruit.demo.repository.*;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class CvMatchSyncTest {
    private final ObjectMapper mapper = new ObjectMapper();

    /** cvmatch gia: tra cac phan hoi da xep hang, ghi lai moi lan goi. */
    static class FakeApi implements CvMatchApi {
        final List<String> calls = new ArrayList<>();
        final Deque<Object> replies = new ArrayDeque<>();
        final ObjectMapper m = new ObjectMapper();
        Map<String, Object> lastBody;

        void reply(int status, String json) {
            replies.add(new Response(status, json == null ? null : m.readTree(json)));
        }

        void down() {
            replies.add(new CvMatchUnavailableException("down", null));
        }

        private Response next(String call, Map<String, Object> body) {
            calls.add(call);
            if (body != null) lastBody = body;
            Object r = replies.poll();
            if (r instanceof RuntimeException e) throw e;
            if (r == null) throw new AssertionError("khong co phan hoi cho " + call);
            return (Response) r;
        }

        @Override public Response postCv(Map<String, Object> cv) { return next("POST /cv", cv); }
        @Override public Response deleteCv(String cvId) { return next("DELETE /cv/" + cvId, null); }
        @Override public Response postJd(Map<String, Object> jd) { return next("POST /jd", jd); }
        @Override public Response patchJdStatus(String jdId, String s) { return next("PATCH " + jdId + " " + s, null); }
        @Override public Response matchJd(String jdId, Map<String, Object> b) { return next("match jd", b); }
        @Override public Response matchCv(String cvId, Map<String, Object> b) { return next("match cv", b); }
        @Override public Response explainForHr(String r, String c) { return next("explain hr", null); }
        @Override public Response explainForCandidate(String r, String j) { return next("explain cand", null); }
        @Override public Response health() { return next("health", null); }
    }

    FakeApi api;
    Map<Integer, MatchCvLink> cvLinkStore;
    Map<Integer, MatchJdLink> jdLinkStore;
    Map<String, List<CvData>> cvRows;
    CvMatchSync sync;
    Job job;

    @BeforeEach
    void setUp() {
        api = new FakeApi();
        cvLinkStore = new HashMap<>();
        jdLinkStore = new HashMap<>();
        cvRows = new HashMap<>();
        var cvLinks = mock(MatchCvLinkRepository.class);
        when(cvLinks.findById(any())).thenAnswer(i -> Optional.ofNullable(cvLinkStore.get(i.<Integer>getArgument(0))));
        when(cvLinks.save(any())).thenAnswer(i -> {
            MatchCvLink l = i.getArgument(0);
            cvLinkStore.put(l.getCandidateId(), l);
            return l;
        });
        when(cvLinks.findByStatusIn(any())).thenAnswer(i -> cvLinkStore.values().stream()
                .filter(l -> i.<Collection<SyncStatus>>getArgument(0).contains(l.getStatus())).toList());
        var jdLinks = mock(MatchJdLinkRepository.class);
        when(jdLinks.findById(any())).thenAnswer(i -> Optional.ofNullable(jdLinkStore.get(i.<Integer>getArgument(0))));
        when(jdLinks.save(any())).thenAnswer(i -> {
            MatchJdLink l = i.getArgument(0);
            jdLinkStore.put(l.getJobId(), l);
            return l;
        });
        when(jdLinks.findByStatusIn(any())).thenAnswer(i -> jdLinkStore.values().stream()
                .filter(l -> i.<Collection<SyncStatus>>getArgument(0).contains(l.getStatus())).toList());

        var candidates = mock(CandidateProfileRepository.class);
        when(candidates.findById(5)).thenReturn(Optional.of(CandidateProfile.builder().id(5).userId(50)
                .address("Hà Nội").build()));
        var cvData = mock(CvDataRepository.class);
        when(cvData.findByCandidateIdAndFieldOrderByIdAsc(eq(5), anyString()))
                .thenAnswer(i -> cvRows.getOrDefault(i.<String>getArgument(1), List.of()));
        when(cvData.findByFieldAndValue("parsing_status", "COMPLETED"))
                .thenReturn(List.of(CvData.builder().candidateId(5).field("parsing_status").value("COMPLETED").build()));

        job = Job.builder().id(7).title("Java Dev").company(Company.builder().id(1).name("C").build())
                .description("Viet API").experienceRequired(BigDecimal.ONE).status(JobStatus.DRAFT).build();
        var jobs = mock(JobRepository.class);
        when(jobs.findById(7)).thenAnswer(i -> Optional.of(job));
        when(jobs.findAll()).thenAnswer(i -> List.of(job));
        var jobSkills = mock(JobSkillRepository.class);
        when(jobSkills.findByJobId(7)).thenReturn(List.of(JobSkill.builder()
                .skill(Skill.builder().name("Java").build()).required(true).build()));

        var identity = mock(IdentityClient.class);
        when(identity.get(50)).thenReturn(new ServiceDtos.UserSnapshot(50, "A", "acct@x.test", null,
                Role.CANDIDATE, UserStatus.ACTIVE));
        var tm = mock(PlatformTransactionManager.class);
        when(tm.getTransaction(any())).thenReturn(new SimpleTransactionStatus());

        sync = new CvMatchSync(api, mapper, cvLinks, jdLinks, candidates, cvData, jobs, jobSkills, identity, tm,
                true);
    }

    private void cv(String field, String value) {
        cvRows.computeIfAbsent(field, k -> new ArrayList<>())
                .add(CvData.builder().candidateId(5).field(field).value(value).build());
    }

    private void uploadedCv() {
        cv("parsing_status", "COMPLETED");
        cv("extracted_profile", "{\"personal_info\":{\"email\":\"cv@x.test\"},\"skills\":[\"Java\"],"
                + "\"experience\":[],\"implied_skills\":[{\"name\":\"JVM\"}]}");
        cv("Kỹ năng", "Java\nSpring");
    }

    @Test
    void cvSyncedOnceThenSkippedUntilContentChanges() {
        uploadedCv();
        api.reply(200, "{\"status\":\"ok\",\"cv_id\":\"u-1\",\"version\":1,\"flags\":[\"low_content\"]}");
        assertEquals(SyncStatus.SYNCED, sync.syncCandidate(5));
        Map<String, Object> sent = api.lastBody;
        assertEquals("acct@x.test", ((Map<?, ?>) sent.get("personal_info")).get("email"));
        assertEquals(List.of("Java", "Spring"), sent.get("skills"));
        assertFalse(sent.containsKey("implied_skills"));
        MatchCvLink link = cvLinkStore.get(5);
        assertEquals("u-1", link.getCvId());
        assertEquals("[\"low_content\"]", link.getFlags());

        assertEquals(SyncStatus.SYNCED, sync.syncCandidate(5));            // khong doi -> khong goi
        assertEquals(1, api.calls.size());

        cv("Kỹ năng", "Docker");
        api.reply(200, "{\"status\":\"ok\",\"cv_id\":\"u-2\",\"version\":2,\"flags\":[]}");
        assertEquals(SyncStatus.SYNCED, sync.syncCandidate(5));
        assertEquals("u-2", cvLinkStore.get(5).getCvId());
        assertEquals(2, cvLinkStore.get(5).getCvVersion());
    }

    @Test
    void failureIsRetriedWithBackoffAndInvalidIsNot() {
        uploadedCv();
        api.down();
        assertEquals(SyncStatus.FAILED, sync.syncCandidate(5));
        assertEquals(1, cvLinkStore.get(5).getAttempts());
        cvLinkStore.get(5).setUpdatedAt(LocalDateTime.now());
        assertEquals(0, sync.retryDue());                                  // chua den han (1 phut)
        cvLinkStore.get(5).setUpdatedAt(LocalDateTime.now().minusMinutes(2));
        api.reply(422, "{\"status\":\"invalid\",\"detail\":{\"errors\":[]}}");
        assertEquals(1, sync.retryDue());
        assertEquals(SyncStatus.INVALID, cvLinkStore.get(5).getStatus());
        assertEquals(0, sync.retryDue());                                  // INVALID khong thu lai
    }

    @Test
    void serverErrorIsFailed() {
        uploadedCv();
        api.reply(500, "{\"status\":\"failed\",\"detail\":{\"error\":\"x\"}}");
        assertEquals(SyncStatus.FAILED, sync.syncCandidate(5));
        assertNull(cvLinkStore.get(5).getContentHash());                   // chua gui duoc -> lan sau gui lai
    }

    @Test
    void cvWithoutExtractedProfileIsInvalidWithoutCall() {
        cv("parsing_status", "COMPLETED");
        assertEquals(SyncStatus.INVALID, sync.syncCandidate(5));
        assertTrue(cvLinkStore.get(5).getLastError().contains("extracted_profile"));
        assertTrue(api.calls.isEmpty());
    }

    @Test
    void notUploadedCvIsIgnored() {
        assertNull(sync.syncCandidate(5));
        assertTrue(api.calls.isEmpty() && cvLinkStore.isEmpty());
    }

    @Test
    void deleteMarksDeletedAndTolerates404() {
        uploadedCv();
        api.reply(200, "{\"status\":\"ok\",\"cv_id\":\"u-1\",\"version\":1,\"flags\":[]}");
        sync.syncCandidate(5);
        api.reply(404, "{\"detail\":\"khong co CV u-1\"}");
        sync.deleteCandidate(5);
        assertEquals(SyncStatus.DELETED, cvLinkStore.get(5).getStatus());
        assertEquals("DELETE /cv/u-1", api.calls.get(1));
    }

    @Test
    void jobContentPostedOnceStatusChangesUsePatch() {
        api.reply(200, "{\"status\":\"ok\",\"jd_id\":\"job-7\",\"version\":1}");
        assertEquals(SyncStatus.SYNCED, sync.syncJob(7));
        assertEquals("draft", api.lastBody.get("status"));
        assertEquals(List.of("POST /jd"), api.calls);

        job.setStatus(JobStatus.PUBLISHED);
        api.reply(200, "{\"jd_id\":\"job-7\",\"version\":1,\"status\":\"open\"}");
        assertEquals(SyncStatus.SYNCED, sync.syncJob(7));
        assertEquals("PATCH job-7 open", api.calls.get(1));

        assertEquals(SyncStatus.SYNCED, sync.syncJob(7));                  // khong doi gi
        assertEquals(2, api.calls.size());

        job.setRequirements("Biet Docker");
        api.reply(200, "{\"status\":\"ok\",\"jd_id\":\"job-7\",\"version\":2}");
        assertEquals(SyncStatus.SYNCED, sync.syncJob(7));
        assertEquals("open", api.lastBody.get("status"));
        assertEquals(2, jdLinkStore.get(7).getJdVersion());
    }

    @Test
    void invalidJobIsNotResentUntilChanged() {
        api.reply(422, "{\"status\":\"invalid\",\"jd_id\":\"job-7\"}");
        assertEquals(SyncStatus.INVALID, sync.syncJob(7));
        assertEquals(SyncStatus.INVALID, sync.syncJob(7));
        assertEquals(1, api.calls.size());
    }

    @Test
    void backfillResetsLinksAndUnchangedJdStillSyncsStatus() {
        api.reply(200, "{\"status\":\"ok\",\"jd_id\":\"job-7\",\"version\":1}");
        sync.syncJob(7);
        assertEquals(Map.of("jd", 1, "cv", 1), sync.backfill("all"));
        assertEquals(SyncStatus.PENDING, jdLinkStore.get(7).getStatus());
        api.reply(200, "{\"status\":\"unchanged\",\"jd_id\":\"job-7\",\"version\":1}");
        api.reply(200, "{\"jd_id\":\"job-7\",\"version\":1,\"status\":\"draft\"}");
        assertEquals(SyncStatus.SYNCED, sync.syncJob(7));
        assertEquals(List.of("POST /jd", "POST /jd", "PATCH job-7 draft"), api.calls);
    }

    @Test
    void syncCanBeSwitchedOff() {
        var tm = mock(PlatformTransactionManager.class);
        assertTrue(new CvMatchSync(api, mapper, null, null, null, null, null, null, null, tm, true).enabled());
        assertFalse(new CvMatchSync(api, mapper, null, null, null, null, null, null, null, tm, false).enabled());
    }

    @Test
    void backoffSchedule() {
        var now = LocalDateTime.of(2026, 11, 24, 10, 0);
        assertTrue(CvMatchSync.due(0, now, now));
        assertFalse(CvMatchSync.due(3, now.minusMinutes(3), now));         // lan 3 -> 4 phut
        assertTrue(CvMatchSync.due(3, now.minusMinutes(4), now));
        assertFalse(CvMatchSync.due(CvMatchSync.MAX_ATTEMPTS, now.minusDays(1), now));
    }
}
