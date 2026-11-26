package recruit.demo.service.cvmatch;

import recruit.demo.enums.JobStatus;
import recruit.demo.enums.Role;
import recruit.demo.enums.SyncStatus;
import recruit.demo.enums.UserStatus;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.ServiceDtos;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class CvMatchMatchingTest {
    final ObjectMapper mapper = new ObjectMapper();
    CvMatchSyncTest.FakeApi api;
    CvMatchSync sync;
    MatchingResultRepository results;
    MatchCvLinkRepository cvLinks;
    MatchJdLinkRepository jdLinks;
    JobApplicationRepository applications;
    List<MatchingResult> store;
    CvMatchMatching matching;
    Job java, closed;
    CandidateProfile cand, other;

    static final String HEALTH = "{\"status\":\"ok\",\"config_hash\":\"abcdef1234567\",\"versions\":"
            + "{\"ontology_version\":\"kb-2026-11-24\",\"rerank_config_version\":\"rr-1.0\"}}";

    @BeforeEach
    void setUp() {
        api = new CvMatchSyncTest.FakeApi();
        sync = mock(CvMatchSync.class);
        store = new ArrayList<>();
        results = mock(MatchingResultRepository.class);
        when(results.save(any())).thenAnswer(i -> {
            MatchingResult m = i.getArgument(0);
            if (m.getId() == null) {
                m.setId(store.size() + 1);
                store.add(m);
            }
            return m;
        });
        doAnswer(i -> store.remove(i.<MatchingResult>getArgument(0))).when(results).delete(any());
        when(results.findFirstByJobIdAndCandidateIdAndEngineAndDirection(any(), any(), any(), any())).thenAnswer(i ->
                store.stream().filter(m -> m.getJob().getId().equals(i.getArgument(0))
                        && m.getCandidate().getId().equals(i.getArgument(1)) && m.getDirection().equals(i.getArgument(3)))
                        .findFirst());
        when(results.findByCandidateAndEngine(any(), any(), any())).thenAnswer(i -> store.stream()
                .filter(m -> m.getCandidate().getId().equals(i.getArgument(0)) && m.getDirection().equals(i.getArgument(2)))
                .toList());
        when(results.findByJobAndEngine(any(), any(), any())).thenAnswer(i -> store.stream()
                .filter(m -> m.getJob().getId().equals(i.getArgument(0)) && m.getDirection().equals(i.getArgument(2)))
                .toList());

        cand = CandidateProfile.builder().id(5).userId(50).build();
        other = CandidateProfile.builder().id(6).userId(60).build();
        cvLinks = mock(MatchCvLinkRepository.class);
        Map<Integer, MatchCvLink> cl = new HashMap<>(Map.of(
                5, MatchCvLink.builder().candidateId(5).cvId("cv-5").status(SyncStatus.SYNCED).build(),
                6, MatchCvLink.builder().candidateId(6).cvId("cv-6").status(SyncStatus.SYNCED).build()));
        when(cvLinks.findById(any())).thenAnswer(i -> Optional.ofNullable(cl.get(i.<Integer>getArgument(0))));
        when(cvLinks.findByCvId(any())).thenAnswer(i -> cl.values().stream()
                .filter(l -> l.getCvId().equals(i.getArgument(0))).findFirst());
        when(cvLinks.findByCandidateIdIn(any())).thenAnswer(i -> i.<Collection<Integer>>getArgument(0).stream()
                .map(cl::get).filter(Objects::nonNull).toList());

        var company = Company.builder().id(1).name("C").build();
        java = Job.builder().id(7).title("Java Dev").company(company).status(JobStatus.PUBLISHED).build();
        closed = Job.builder().id(8).title("Old").company(company).status(JobStatus.CLOSED).build();
        var jobs = mock(JobRepository.class);
        when(jobs.findById(7)).thenReturn(Optional.of(java));
        when(jobs.findById(8)).thenReturn(Optional.of(closed));
        jdLinks = mock(MatchJdLinkRepository.class);
        when(jdLinks.findById(7)).thenReturn(Optional.of(MatchJdLink.builder().jobId(7).jdId("job-7")
                .jdStatus("open").status(SyncStatus.SYNCED).build()));
        var candidates = mock(CandidateProfileRepository.class);
        when(candidates.findById(5)).thenReturn(Optional.of(cand));
        when(candidates.findById(6)).thenReturn(Optional.of(other));
        applications = mock(JobApplicationRepository.class);
        var identity = mock(IdentityClient.class);
        when(identity.get(anyInt())).thenAnswer(i -> new ServiceDtos.UserSnapshot(i.getArgument(0), "U" + i.getArgument(0),
                null, null, Role.CANDIDATE, UserStatus.ACTIVE));

        matching = new CvMatchMatching(api, sync, mapper, results, cvLinks, jdLinks, jobs, candidates, applications,
                identity, 20, 50);
    }

    @Test
    void candidateRefreshMapsScoresSkipsClosedJobsAndDropsStaleRows() {
        api.reply(200, """
            {"run_id":"r1","items":[
              {"jd_id":"job-7","jd_version":1,"rank":1,"score":83,"band":"high","cap_applied":false,"flags":["x"],
               "features":{"A1":0.875,"B4":0.6,"B1":1.0,"B2":0.5,"A2":null},
               "skills":{"met":["Java","Spring Boot"],"partial":["SQL"],"missing":["Docker"]}},
              {"jd_id":"job-8","jd_version":1,"rank":2,"score":40,"band":"low","cap_applied":true,"flags":[],
               "features":{},"skills":{"met":[],"partial":[],"missing":[]}},
              {"jd_id":"E2E-X","rank":3,"score":10,"band":"low","cap_applied":false,"flags":[],"features":{},"skills":{}}]}
            """);
        api.reply(200, HEALTH);
        var out = matching.refreshForCandidate(cand);
        assertEquals(1, out.size());
        var r = out.get(0);
        assertEquals(new BigDecimal("0.8300"), r.overallScore());
        assertEquals(new BigDecimal("0.8750"), r.skillOverlap());
        assertEquals(new BigDecimal("0.6000"), r.semanticSimilarity());
        assertEquals(List.of("Java", "Spring Boot"), r.matchedSkills());
        assertEquals(List.of("Docker"), r.missingSkills());
        assertEquals(List.of("SQL"), r.partialSkills());
        assertEquals("high", r.band());
        assertEquals("cvmatch-kb-2026-11-24/rr-1.0/abcdef12", r.modelVersion());
        assertEquals(1, r.rankPosition());
        MatchingResult row = store.get(0);
        assertEquals("cv_to_jd", row.getDirection());
        assertEquals("cv-5", row.getCvmatchCvId());
        assertEquals("{N=20}", api.lastBody.toString());

        // lan sau khong con job-7 -> dong cu bi xoa
        api.reply(200, "{\"run_id\":\"r2\",\"items\":[]}");
        assertEquals(List.of(), matching.refreshForCandidate(cand));
        assertTrue(store.isEmpty());
    }

    @Test
    void recruiterRefreshUsesApplicantsOnly() {
        when(applications.findByJobId(7)).thenReturn(List.of(JobApplication.builder().candidate(other).job(java).build()));
        api.reply(200, """
            {"run_id":"r9","items":[{"cv_id":"cv-6","rank":1,"score":70,"band":"mid","cap_applied":false,"flags":[],
              "features":{"A1":0.5},"skills":{"met":["Java"],"partial":[],"missing":[]}}]}
            """);
        api.reply(200, HEALTH);
        var out = matching.refreshForJob(java, false);
        assertEquals(List.of("cv-6"), api.lastBody.get("include_cv_ids"));
        assertEquals(6, out.get(0).candidateId());
        assertEquals("U60", out.get(0).candidateName());
        assertEquals("jd_to_cv", store.get(0).getDirection());
    }

    @Test
    void recruiterRefreshWithoutApplicantsDoesNotCall() {
        when(applications.findByJobId(7)).thenReturn(List.of());
        assertEquals(List.of(), matching.refreshForJob(java, false));
        assertTrue(api.calls.isEmpty());
    }

    @Test
    void notSyncedCvTriesSyncThenReportsClearly() {
        CandidateProfile fresh = CandidateProfile.builder().id(9).userId(90).build();
        var ex = assertThrows(ApiException.class, () -> matching.refreshForCandidate(fresh));
        assertEquals(503, ex.getStatus().value());
        verify(sync).syncCandidate(9);

        when(cvLinks.findById(9)).thenReturn(Optional.of(MatchCvLink.builder().candidateId(9)
                .status(SyncStatus.INVALID).lastError("thieu extracted_profile").build()));
        var ex2 = assertThrows(ApiException.class, () -> matching.refreshForCandidate(fresh));
        assertEquals(422, ex2.getStatus().value());
    }

    @Test
    void cvmatchErrorsMapToClearStatuses() {
        api.reply(409, "{\"detail\":\"CV chua nap theo bo khoa hien tai\"}");
        assertEquals(409, assertThrows(ApiException.class, () -> matching.refreshForCandidate(cand)).getStatus().value());
        api.reply(500, "{\"detail\":\"boom\"}");
        assertEquals(502, assertThrows(ApiException.class, () -> matching.refreshForCandidate(cand)).getStatus().value());
    }

    @Test
    void explanationIsFetchedOnceAndCandidateNeverSeesScore() {
        api.reply(200, "{\"run_id\":\"r1\",\"items\":[{\"jd_id\":\"job-7\",\"rank\":1,\"score\":83,\"band\":\"high\","
                + "\"cap_applied\":false,\"flags\":[],\"features\":{},\"skills\":{}}]}");
        api.reply(200, HEALTH);
        matching.refreshForCandidate(cand);
        MatchingResult m = store.get(0);
        api.reply(200, "{\"mode\":\"template\",\"score\":83,\"band\":\"high\",\"band_label\":\"phù hợp cao\","
                + "\"cap_applied\":false,\"text\":\"Dong 1\\n• Dong 2\",\"sections\":{\"skills\":{}}}");
        var e = matching.explanation(m);
        assertEquals("candidate", e.audience());
        assertNull(e.score());
        assertEquals("phù hợp cao", e.bandLabel());
        assertEquals("explain cand", api.calls.get(api.calls.size() - 1));
        int n = api.calls.size();
        matching.explanation(m);                                          // lan 2: doc DB
        assertEquals(n, api.calls.size());
        assertEquals(List.of("Dong 1", "Dong 2"), matching.toResponse(m).reasons());
    }

    @Test
    void staleRunGivesConflict() {
        MatchingResult m = MatchingResult.builder().id(1).job(java).candidate(cand).engine("cvmatch")
                .direction("jd_to_cv").runId("gone").cvmatchCvId("cv-5").overallScore(BigDecimal.ONE).build();
        api.reply(404, "{\"detail\":\"khong co run\"}");
        assertEquals(409, assertThrows(ApiException.class, () -> matching.explanation(m)).getStatus().value());
    }
}
