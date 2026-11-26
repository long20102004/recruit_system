package recruit.demo.service.cvmatch;

import recruit.demo.enums.JobStatus;
import recruit.demo.enums.SyncStatus;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import recruit.demo.client.CvMatchApi;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.MatchingDtos;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

/**
 * Matching bang cvmatch (plan I06). Ham o day chay TRONG giao dich cua {@code MatchingService} (quyen da kiem o do).
 *
 * <ul>
 *   <li>Ung vien "Phu hop voi toi": Luong D ({@code POST /match/cv/{cv_id}}), MOT lan goi cho moi job dang mo.</li>
 *   <li>Recruiter "Ghep ho so": Luong C ({@code POST /match/jd/job-<id>}) gioi han ung vien da nop don
 *       ({@code include_cv_ids}); admin co the xet ca kho ({@code scope=pool}).</li>
 *   <li>Hai chieu luu rieng ({@code direction}); diem 0-100 cua cvmatch -> 0-1 theo hop dong frontend.</li>
 * </ul>
 */
@Slf4j
@Service
public class CvMatchMatching {
    public static final String ENGINE = "cvmatch";
    public static final String TO_CV = "jd_to_cv";
    public static final String TO_JD = "cv_to_jd";
    static final String MODEL_NAME = "cvmatch";

    private final CvMatchApi api;
    private final CvMatchSync sync;
    private final ObjectMapper mapper;
    private final MatchingResultRepository results;
    private final MatchCvLinkRepository cvLinks;
    private final MatchJdLinkRepository jdLinks;
    private final JobRepository jobs;
    private final CandidateProfileRepository candidates;
    private final JobApplicationRepository applications;
    private final IdentityClient identity;
    private final int candidateN;
    private final int recruiterN;
    private volatile String modelVersion;
    private volatile long modelVersionAt;

    public CvMatchMatching(CvMatchApi api, CvMatchSync sync, ObjectMapper mapper, MatchingResultRepository results,
                           MatchCvLinkRepository cvLinks, MatchJdLinkRepository jdLinks, JobRepository jobs,
                           CandidateProfileRepository candidates, JobApplicationRepository applications,
                           IdentityClient identity,
                           @Value("${app.cvmatch.candidate-n:20}") int candidateN,
                           @Value("${app.cvmatch.recruiter-n:50}") int recruiterN) {
        this.api = api;
        this.sync = sync;
        this.mapper = mapper;
        this.results = results;
        this.cvLinks = cvLinks;
        this.jdLinks = jdLinks;
        this.jobs = jobs;
        this.candidates = candidates;
        this.applications = applications;
        this.identity = identity;
        this.candidateN = candidateN;
        this.recruiterN = recruiterN;
    }

    // ------------------------------------------------------------------------------------------- ung vien

    public List<MatchingDtos.MatchResponse> resultsForCandidate(CandidateProfile c) {
        return sortByRank(results.findByCandidateAndEngine(c.getId(), ENGINE, TO_JD)).stream()
                .filter(m -> m.getJob().getStatus() == JobStatus.PUBLISHED).map(this::toResponse).toList();
    }

    public List<MatchingDtos.MatchResponse> refreshForCandidate(CandidateProfile c) {
        String cvId = requireCv(c);
        JsonNode out = call(api.matchCv(cvId, Map.of("N", candidateN)), "match CV");
        List<MatchingResult> saved = saveItems(out, TO_JD, c, null, cvId);
        Set<Integer> keep = new HashSet<>();
        saved.forEach(m -> keep.add(m.getId()));
        for (MatchingResult old : results.findByCandidateAndEngine(c.getId(), ENGINE, TO_JD)) {
            if (!keep.contains(old.getId())) results.delete(old);          // ket qua dan xuat cua lan chay truoc
        }
        return saved.stream().map(this::toResponse).toList();
    }

    /** Ung vien cham mot job (vd trang chi tiet job). */
    public MatchingDtos.MatchResponse runForCandidate(CandidateProfile c, Job job) {
        String cvId = requireCv(c);
        String jdId = requireJd(job);
        JsonNode out = call(api.matchCv(cvId, Map.of("include_jd_ids", List.of(jdId), "N", 1)), "match CV");
        List<MatchingResult> saved = saveItems(out, TO_JD, c, null, cvId);
        if (saved.isEmpty()) {
            throw new ApiException(HttpStatus.CONFLICT, "Việc làm chưa mở hoặc chưa sẵn sàng để ghép hồ sơ");
        }
        return toResponse(saved.get(0));
    }

    // ------------------------------------------------------------------------------------------- recruiter

    public List<MatchingDtos.MatchResponse> resultsForJob(Job job) {
        return sortByRank(results.findByJobAndEngine(job.getId(), ENGINE, TO_CV)).stream().map(this::toResponse).toList();
    }

    /** @param pool true: xet ca kho CV (chi admin); false: chi ung vien da nop don. */
    public List<MatchingDtos.MatchResponse> refreshForJob(Job job, boolean pool) {
        String jdId = requireJd(job);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("N", recruiterN);
        if (!pool) {
            List<Integer> ids = applications.findByJobId(job.getId()).stream().map(a -> a.getCandidate().getId()).toList();
            List<String> cvIds = new ArrayList<>();
            for (MatchCvLink l : cvLinks.findByCandidateIdIn(ids)) {
                if (l.getStatus() == SyncStatus.SYNCED && l.getCvId() != null) cvIds.add(l.getCvId());
            }
            if (cvIds.isEmpty()) return List.of();
            body.put("include_cv_ids", cvIds);
        }
        JsonNode out = call(api.matchJd(jdId, body), "match JD");
        List<MatchingResult> saved = saveItems(out, TO_CV, null, job, null);
        Set<Integer> keep = new HashSet<>();
        saved.forEach(m -> keep.add(m.getId()));
        for (MatchingResult old : results.findByJobAndEngine(job.getId(), ENGINE, TO_CV)) {
            if (!keep.contains(old.getId())) results.delete(old);
        }
        return saved.stream().map(this::toResponse).toList();
    }

    /** Recruiter cham mot ung vien cho job cua minh. */
    public MatchingDtos.MatchResponse runForRecruiter(Job job, CandidateProfile c) {
        String jdId = requireJd(job);
        String cvId = requireCv(c);
        JsonNode out = call(api.matchJd(jdId, Map.of("include_cv_ids", List.of(cvId), "N", 1)), "match JD");
        List<MatchingResult> saved = saveItems(out, TO_CV, null, job, null);
        if (saved.isEmpty()) throw new ApiException(HttpStatus.CONFLICT, "CV của ứng viên chưa sẵn sàng để ghép");
        return toResponse(saved.get(0));
    }

    // ------------------------------------------------------------------------------------------- giai thich

    public MatchingDtos.ExplanationResponse explanation(MatchingResult m) {
        boolean candidateView = TO_JD.equals(m.getDirection());
        String audience = candidateView ? "candidate" : "hr";
        if (m.getExplanationJson() != null) return explanationOf(m, audience, m.getExplanationJson());
        if (m.getRunId() == null || m.getCvmatchCvId() == null) {
            throw new ApiException(HttpStatus.CONFLICT, "Kết quả chưa có giải thích; hãy chạy lại ghép hồ sơ");
        }
        CvMatchApi.Response r = candidateView
                ? api.explainForCandidate(m.getRunId(), CvMatchPayloads.jdId(m.getJob().getId()))
                : api.explainForHr(m.getRunId(), m.getCvmatchCvId());
        if (r.status() == 404) {
            throw new ApiException(HttpStatus.CONFLICT, "Kết quả ghép đã cũ (dữ liệu AI đã dựng lại); hãy chạy lại ghép hồ sơ");
        }
        JsonNode body = call(r, "explain");
        Map<String, Object> stored = mapper.convertValue(body, Map.class);
        m.setExplanationJson(stored);
        m.setExplanation(body.path("text").asString(""));
        results.save(m);
        return explanationOf(m, audience, stored);
    }

    @SuppressWarnings("unchecked")
    private MatchingDtos.ExplanationResponse explanationOf(MatchingResult m, String audience, Map<String, Object> e) {
        Object score = e.get("score");
        return new MatchingDtos.ExplanationResponse(m.getId(), audience, (String) e.get("band"), (String) e.get("band_label"),
                "candidate".equals(audience) ? null : score instanceof Number n ? n.intValue() : null,
                (Boolean) e.get("cap_applied"), (String) e.get("text"), e.get("sections"));
    }

    // ------------------------------------------------------------------------------------------- noi bo

    /** CV da o cvmatch (thu dong bo ngay neu chua) -> cv_id. */
    String requireCv(CandidateProfile c) {
        MatchCvLink link = cvLinks.findById(c.getId()).orElse(null);
        if (link == null || link.getStatus() != SyncStatus.SYNCED) {
            sync.syncCandidate(c.getId());
            link = cvLinks.findById(c.getId()).orElse(null);
        }
        if (link != null && link.getStatus() == SyncStatus.SYNCED && link.getCvId() != null) return link.getCvId();
        if (link != null && link.getStatus() == SyncStatus.INVALID) {
            throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "CV chưa dùng được để ghép việc làm; hãy tải lại CV (" + Objects.toString(link.getLastError(), "") + ")");
        }
        throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "CV đang được xử lý cho việc ghép hồ sơ, hãy thử lại sau ít phút");
    }

    String requireJd(Job job) {
        MatchJdLink link = jdLinks.findById(job.getId()).orElse(null);
        if (link == null || link.getStatus() != SyncStatus.SYNCED
                || !CvMatchPayloads.jdStatus(job.getStatus()).equals(link.getJdStatus())) {
            sync.syncJob(job.getId());
            link = jdLinks.findById(job.getId()).orElse(null);
        }
        if (link != null && link.getStatus() == SyncStatus.SYNCED) return link.getJdId();
        if (link != null && link.getStatus() == SyncStatus.INVALID) {
            throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "Tin tuyển dụng thiếu nội dung để ghép hồ sơ (cần kỹ năng, yêu cầu hoặc mô tả công việc)");
        }
        throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Tin tuyển dụng đang được xử lý cho việc ghép hồ sơ, hãy thử lại sau");
    }

    private JsonNode call(CvMatchApi.Response r, String what) {
        if (r.ok() && r.body() != null) return r.body();
        if (r.status() == 404 || r.status() == 409) {
            throw new ApiException(HttpStatus.CONFLICT, "Dữ liệu ghép hồ sơ chưa sẵn sàng (" + what + ": " + r.detail() + ")");
        }
        throw new ApiException(HttpStatus.BAD_GATEWAY, "Dịch vụ ghép hồ sơ lỗi (" + what + ": " + r.detail() + ")");
    }

    /**
     * Ghi / cap nhat mot dong moi item. Chieu cv_to_jd: {@code candidate} co dinh, item la JD; chieu jd_to_cv:
     * {@code job} co dinh, item la CV.
     */
    List<MatchingResult> saveItems(JsonNode out, String direction, CandidateProfile candidate, Job job, String cvId) {
        String version = modelVersion();
        String runId = out.path("run_id").asString(null);
        List<MatchingResult> saved = new ArrayList<>();
        Map<String, Integer> candidateOfCv = new HashMap<>();
        if (TO_CV.equals(direction)) {
            List<String> ids = new ArrayList<>();
            out.path("items").forEach(it -> ids.add(it.path("cv_id").asString()));
            for (String id : ids) cvLinks.findByCvId(id).ifPresent(l -> candidateOfCv.put(id, l.getCandidateId()));
        }
        for (JsonNode it : out.path("items")) {
            Job j = job;
            CandidateProfile c = candidate;
            String itemCv = cvId;
            if (TO_JD.equals(direction)) {
                Integer jobId = CvMatchPayloads.jobIdOf(it.path("jd_id").asString(null));
                j = jobId == null ? null : jobs.findById(jobId).orElse(null);
                if (j == null || j.getStatus() != JobStatus.PUBLISHED) continue;       // lech dong bo: bo qua
            } else {
                itemCv = it.path("cv_id").asString(null);
                Integer cid = candidateOfCv.get(itemCv);
                c = cid == null ? null : candidates.findById(cid).orElse(null);
                if (c == null) continue;
            }
            MatchingResult m = results.findFirstByJobIdAndCandidateIdAndEngineAndDirection(j.getId(), c.getId(), ENGINE,
                    direction).orElseGet(MatchingResult::new);
            apply(m, it, j, c, direction, runId, itemCv, version);
            saved.add(results.save(m));
        }
        return saved;
    }

    static void apply(MatchingResult m, JsonNode it, Job job, CandidateProfile c, String direction, String runId,
                      String cvId, String version) {
        JsonNode f = it.path("features");
        JsonNode sk = it.path("skills");
        m.setJob(job);
        m.setCandidate(c);
        m.setEngine(ENGINE);
        m.setDirection(direction);
        m.setModelName(MODEL_NAME);
        m.setModelVersion(version);
        m.setCvId(null);
        m.setOverallScore(BigDecimal.valueOf(it.path("score").asInt()).movePointLeft(2).setScale(4, RoundingMode.HALF_UP));
        m.setSkillsScore(score(f.path("A1")));
        m.setSemanticScore(score(f.path("B4")));
        m.setExperienceScore(score(f.path("B2")));
        m.setMatchedSkills(strings(sk.path("met")));
        m.setMissingSkills(strings(sk.path("missing")));
        m.setBand(it.path("band").asString(null));
        m.setCapApplied(it.path("cap_applied").asBoolean(false));
        List<String> flags = new ArrayList<>(strings(it.path("flags")));
        for (String p : strings(sk.path("partial"))) flags.add("partial:" + p);
        m.setFlags(flags);
        m.setRankPosition(it.path("rank").isNumber() ? it.path("rank").asInt() : null);
        if (!Objects.equals(runId, m.getRunId())) {          // lan chay moi -> giai thich cu khong con dung
            m.setExplanation(null);
            m.setExplanationJson(null);
        }
        m.setRunId(runId);
        m.setCvmatchCvId(cvId);
    }

    private static BigDecimal score(JsonNode v) {
        return v.isNumber() ? BigDecimal.valueOf(v.asDouble()).setScale(4, RoundingMode.HALF_UP) : null;
    }

    private static List<String> strings(JsonNode arr) {
        List<String> out = new ArrayList<>();
        if (arr != null && arr.isArray()) arr.forEach(x -> { if (!x.asString("").isBlank()) out.add(x.asString()); });
        return out;
    }

    /** "ontology/rerank/hash8" tu /health cua cvmatch (cache 60 s). */
    String modelVersion() {
        long now = System.currentTimeMillis();
        if (modelVersion != null && now - modelVersionAt < 60_000) return modelVersion;
        try {
            CvMatchApi.Response h = api.health();
            if (h.ok() && h.body() != null) {
                JsonNode v = h.body().path("versions");
                String hash = h.body().path("config_hash").asString("");
                modelVersion = v.path("ontology_version").asString("?") + "/" + v.path("rerank_config_version").asString("?")
                        + "/" + (hash.length() > 8 ? hash.substring(0, 8) : hash);
                modelVersionAt = now;
            }
        } catch (CvMatchApi.CvMatchUnavailableException ex) {
            log.warn("cvmatch health: {}", ex.getMessage());
        }
        return modelVersion == null ? "unknown" : modelVersion;
    }

    private static List<MatchingResult> sortByRank(List<MatchingResult> rows) {
        List<MatchingResult> out = new ArrayList<>(rows);
        out.sort(Comparator.comparing((MatchingResult m) -> m.getRankPosition() == null ? Integer.MAX_VALUE : m.getRankPosition())
                .thenComparing(MatchingResult::getOverallScore, Comparator.reverseOrder()));
        return out;
    }

    public MatchingDtos.MatchResponse toResponse(MatchingResult m) {
        List<String> reasons = new ArrayList<>();
        if (m.getExplanation() != null) {
            for (String line : m.getExplanation().split("\\R")) {
                String s = line.replaceFirst("^[•\\-*\\s]+", "").trim();
                if (!s.isEmpty()) reasons.add(s);
            }
        }
        List<String> partial = new ArrayList<>();
        List<String> flags = new ArrayList<>();
        for (String f : m.getFlags() == null ? List.<String>of() : m.getFlags()) {
            if (f.startsWith("partial:")) partial.add(f.substring("partial:".length()));
            else flags.add(f);
        }
        String name;
        try {
            name = identity.get(m.getCandidate().getUserId()).fullName();
        } catch (RuntimeException ex) {
            name = null;
        }
        return new MatchingDtos.MatchResponse(m.getId(), m.getJob().getId(), m.getJob().getTitle(),
                m.getJob().getCompany().getName(), m.getCandidate().getId(), name, m.getOverallScore(),
                m.getSemanticScore(), null, m.getSkillsScore(),
                m.getMatchedSkills() == null ? List.of() : m.getMatchedSkills(),
                m.getMissingSkills() == null ? List.of() : m.getMissingSkills(), reasons,
                MODEL_NAME + "-" + m.getModelVersion(), m.getRankPosition(), m.getCreatedAt(), m.getBand(),
                m.getCapApplied(), ENGINE, m.getExplanationJson() != null || m.getRunId() != null, partial);
    }
}
