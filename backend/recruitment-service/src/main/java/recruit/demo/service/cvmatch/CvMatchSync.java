package recruit.demo.service.cvmatch;

import recruit.demo.enums.SyncStatus;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import recruit.demo.client.CvMatchApi;
import recruit.demo.client.IdentityClient;
import recruit.demo.entity.*;
import recruit.demo.repository.*;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Dong bo CV / JD tu recruitment DB (nguon su that) sang cvmatch (plan I05).
 *
 * <ul>
 *   <li>Goi sau khi giao dich luu CV / job da commit ({@link CvMatchSyncListener}); loi khong lam hong thao tac goc.</li>
 *   <li>{@code content_hash}: noi dung khong doi -> khong gui lai. JD: hash khong tinh status; doi status -> PATCH.</li>
 *   <li>Loi tam thoi -> {@code FAILED}, {@link #retryDue()} thu lai co backoff; 422 -> {@code INVALID} (cho du lieu doi).</li>
 *   <li>{@link #backfill(String)} danh dau moi CV / job la PENDING: dung lai cvmatch-db tu MySQL.</li>
 * </ul>
 */
@Slf4j
@Service
public class CvMatchSync {
    static final String PARSING_STATUS = "parsing_status";
    static final String EXTRACTED_PROFILE = "extracted_profile";
    static final List<String> FORM_FIELDS = List.of(CvMatchPayloads.F_SKILLS, CvMatchPayloads.F_SUMMARY,
            CvMatchPayloads.F_CERTS, CvMatchPayloads.F_EXPERIENCE, CvMatchPayloads.F_EDUCATION);
    static final int MAX_ATTEMPTS = 12;

    private final CvMatchApi api;
    private final ObjectMapper mapper;
    private final MatchCvLinkRepository cvLinks;
    private final MatchJdLinkRepository jdLinks;
    private final CandidateProfileRepository candidates;
    private final CvDataRepository cvData;
    private final JobRepository jobs;
    private final JobSkillRepository jobSkills;
    private final IdentityClient identity;
    private final TransactionTemplate tx;
    private final boolean enabled;
    private final Map<String, Object> locks = new ConcurrentHashMap<>();

    public CvMatchSync(CvMatchApi api, ObjectMapper mapper, MatchCvLinkRepository cvLinks, MatchJdLinkRepository jdLinks,
                       CandidateProfileRepository candidates, CvDataRepository cvData, JobRepository jobs,
                       JobSkillRepository jobSkills, IdentityClient identity, PlatformTransactionManager txManager,
                       @Value("${app.cvmatch.sync.enabled:true}") boolean enabled) {
        this.api = api;
        this.mapper = mapper;
        this.cvLinks = cvLinks;
        this.jdLinks = jdLinks;
        this.candidates = candidates;
        this.cvData = cvData;
        this.jobs = jobs;
        this.jobSkills = jobSkills;
        this.identity = identity;
        this.tx = new TransactionTemplate(txManager);
        this.enabled = enabled;                     // CVMATCH_SYNC_ENABLED=false: tat (vd chay khong co cvmatch)
    }

    public boolean enabled() {
        return enabled;
    }

    // ------------------------------------------------------------------------------------------- CV

    record CvSource(Map<String, Object> payload, String problem) {
    }

    /** Dong bo CV cua mot ung vien. Tra ve trang thai sau khi chay (null = khong co gi de gui). */
    public SyncStatus syncCandidate(Integer candidateId) {
        synchronized (lock("cv:" + candidateId)) {
            CvSource src;
            try {
                src = tx.execute(s -> loadCv(candidateId));
            } catch (RuntimeException ex) {          // vd identity-service khong tra loi (can email tai khoan)
                MatchCvLink link = cvLinks.findById(candidateId).orElseGet(() ->
                        MatchCvLink.builder().candidateId(candidateId).status(SyncStatus.PENDING).build());
                return save(link, SyncStatus.FAILED, "doc CV: " + ex, true);
            }
            if (src == null) return null;
            MatchCvLink link = cvLinks.findById(candidateId)
                    .orElseGet(() -> MatchCvLink.builder().candidateId(candidateId).status(SyncStatus.PENDING).build());
            if (src.problem() != null) {
                return save(link, SyncStatus.INVALID, src.problem(), false);
            }
            String hash = CvMatchPayloads.contentHash(mapper, src.payload());
            if (link.getStatus() == SyncStatus.SYNCED && hash.equals(link.getContentHash())) return SyncStatus.SYNCED;
            try {
                CvMatchApi.Response r = api.postCv(src.payload());
                JsonNode b = r.body();
                String st = b == null ? "" : b.path("status").asString("");
                if (r.ok() && ("ok".equals(st) || "duplicate".equals(st))) {
                    link.setCvId(b.path("cv_id").asString(null));
                    if (b.path("version").isNumber()) link.setCvVersion(b.path("version").asInt());
                    link.setFlags(b.path("flags").isArray() ? b.path("flags").toString() : null);
                    link.setContentHash(hash);
                    link.setSyncedAt(LocalDateTime.now());
                    return save(link, SyncStatus.SYNCED, null, false);
                }
                if (r.status() == 422) {
                    link.setContentHash(hash);
                    return save(link, SyncStatus.INVALID, r.detail() + " " + b, false);
                }
                return save(link, SyncStatus.FAILED, r.detail(), true);
            } catch (CvMatchApi.CvMatchUnavailableException ex) {
                return save(link, SyncStatus.FAILED, ex.getMessage(), true);
            }
        }
    }

    CvSource loadCv(Integer candidateId) {
        CandidateProfile c = candidates.findById(candidateId).orElse(null);
        if (c == null) return null;
        if (!"COMPLETED".equals(first(candidateId, PARSING_STATUS))) return null;
        String extracted = first(candidateId, EXTRACTED_PROFILE);
        if (extracted.isBlank()) {
            return new CvSource(null, "CV khong co extracted_profile (du lieu cu): ung vien can tai lai CV");
        }
        Map<String, Object> profile;
        try {
            profile = mapper.readValue(extracted, Map.class);
        } catch (Exception ex) {
            return new CvSource(null, "extracted_profile khong doc duoc: " + ex.getClass().getSimpleName());
        }
        Map<String, List<String>> form = new LinkedHashMap<>();
        for (String f : FORM_FIELDS) {
            List<CvData> rows = cvData.findByCandidateIdAndFieldOrderByIdAsc(candidateId, f);
            List<String> lines = new ArrayList<>();
            for (CvData row : rows) {
                if (row.getValue() == null) continue;
                for (String line : row.getValue().split("\\R")) if (!line.isBlank()) lines.add(line.trim());
            }
            form.put(f, lines);
        }
        String email = identity.get(c.getUserId()).email();
        return new CvSource(CvMatchPayloads.cvPayload(profile, form, email, c.getAddress()), null);
    }

    /** Xoa CV ben cvmatch (vd tai khoan bi xoa). 404 = da khong con. */
    public void deleteCandidate(Integer candidateId) {
        synchronized (lock("cv:" + candidateId)) {
            cvLinks.findById(candidateId).ifPresent(link -> {
                if (link.getCvId() == null) {
                    cvLinks.delete(link);
                    return;
                }
                try {
                    CvMatchApi.Response r = api.deleteCv(link.getCvId());
                    if (r.ok() || r.status() == 404) save(link, SyncStatus.DELETED, null, false);
                    else save(link, SyncStatus.FAILED, "delete " + r.detail(), true);
                } catch (CvMatchApi.CvMatchUnavailableException ex) {
                    save(link, SyncStatus.FAILED, "delete " + ex.getMessage(), true);
                }
            });
        }
    }

    // ------------------------------------------------------------------------------------------- JD

    record JdSource(Map<String, Object> payload, String status) {
    }

    public SyncStatus syncJob(Integer jobId) {
        synchronized (lock("jd:" + jobId)) {
            JdSource src = tx.execute(s -> loadJob(jobId));
            if (src == null) return null;
            MatchJdLink link = jdLinks.findById(jobId).orElseGet(() -> MatchJdLink.builder().jobId(jobId)
                    .jdId(CvMatchPayloads.jdId(jobId)).status(SyncStatus.PENDING).build());
            String hash = CvMatchPayloads.contentHash(mapper, src.payload());
            boolean contentSynced = hash.equals(link.getContentHash())
                    && (link.getStatus() == SyncStatus.SYNCED || link.getStatus() == SyncStatus.INVALID);
            if (contentSynced && link.getStatus() == SyncStatus.INVALID) return SyncStatus.INVALID;
            if (contentSynced && src.status().equals(link.getJdStatus())) return SyncStatus.SYNCED;
            try {
                CvMatchApi.Response r;
                if (!contentSynced) {
                    Map<String, Object> body = new LinkedHashMap<>(src.payload());
                    body.put("status", src.status());
                    r = api.postJd(body);
                    JsonNode b = r.body();
                    String st = b == null ? "" : b.path("status").asString("");
                    if (r.status() == 422) {
                        link.setContentHash(hash);
                        return saveJd(link, SyncStatus.INVALID, r.detail() + " " + b, false);
                    }
                    if (!r.ok() || !("ok".equals(st) || "unchanged".equals(st))) {
                        return saveJd(link, SyncStatus.FAILED, r.detail(), true);
                    }
                    if (b.path("version").isNumber()) link.setJdVersion(b.path("version").asInt());
                    link.setContentHash(hash);
                    if ("ok".equals(st)) link.setJdStatus(src.status());
                }
                if (!src.status().equals(link.getJdStatus())) {
                    r = api.patchJdStatus(link.getJdId(), src.status());
                    if (!r.ok()) return saveJd(link, SyncStatus.FAILED, "status " + r.detail(), true);
                    link.setJdStatus(src.status());
                }
                link.setSyncedAt(LocalDateTime.now());
                return saveJd(link, SyncStatus.SYNCED, null, false);
            } catch (CvMatchApi.CvMatchUnavailableException ex) {
                return saveJd(link, SyncStatus.FAILED, ex.getMessage(), true);
            }
        }
    }

    JdSource loadJob(Integer jobId) {
        Job job = jobs.findById(jobId).orElse(null);
        if (job == null) return null;
        List<CvMatchPayloads.JobSkillItem> skills = jobSkills.findByJobId(jobId).stream()
                .map(js -> new CvMatchPayloads.JobSkillItem(js.getSkill().getName(), js.isRequired())).toList();
        Map<String, Object> payload = CvMatchPayloads.jdPayload(job.getId(), job.getTitle(),
                job.getCompany().getDescription(), job.getWorkLocation(), job.getEmploymentType(),
                job.getExperienceRequired(), job.getDescription(), job.getRequirements(), job.getResponsibilities(),
                skills);
        return new JdSource(payload, CvMatchPayloads.jdStatus(job.getStatus()));
    }

    // ------------------------------------------------------------------------------------------- thu lai, backfill

    /** Thu lai PENDING / FAILED den han (backoff 1, 2, 4 ... 60 phut theo so lan loi). */
    public int retryDue() {
        if (!enabled) return 0;
        int n = 0;
        LocalDateTime now = LocalDateTime.now();
        for (MatchJdLink l : jdLinks.findByStatusIn(List.of(SyncStatus.PENDING, SyncStatus.FAILED))) {
            if (due(l.getAttempts(), l.getUpdatedAt(), now)) {
                syncJob(l.getJobId());
                n++;
            }
        }
        for (MatchCvLink l : cvLinks.findByStatusIn(List.of(SyncStatus.PENDING, SyncStatus.FAILED))) {
            if (due(l.getAttempts(), l.getUpdatedAt(), now)) {
                syncCandidate(l.getCandidateId());
                n++;
            }
        }
        return n;
    }

    static boolean due(int attempts, LocalDateTime updatedAt, LocalDateTime now) {
        if (attempts >= MAX_ATTEMPTS) return false;
        if (attempts == 0 || updatedAt == null) return true;
        long minutes = Math.min(60, 1L << Math.min(attempts - 1, 6));
        return !updatedAt.plus(Duration.ofMinutes(minutes)).isAfter(now);
    }

    /** Danh dau toan bo la PENDING (attempts = 0); scheduler / lan goi sau se gui. Tra ve so muc da danh dau. */
    public Map<String, Integer> backfill(String scope) {
        int nJd = 0, nCv = 0;
        if (!"cv".equals(scope)) {
            for (Job j : jobs.findAll()) {
                MatchJdLink l = jdLinks.findById(j.getId()).orElseGet(() -> MatchJdLink.builder().jobId(j.getId())
                        .jdId(CvMatchPayloads.jdId(j.getId())).build());
                l.setStatus(SyncStatus.PENDING);
                l.setContentHash(null);
                l.setJdStatus(null);
                l.setAttempts(0);
                jdLinks.save(l);
                nJd++;
            }
        }
        if (!"jd".equals(scope)) {
            Set<Integer> ids = new TreeSet<>();
            for (CvData row : cvData.findByFieldAndValue(PARSING_STATUS, "COMPLETED")) ids.add(row.getCandidateId());
            for (Integer id : ids) {
                MatchCvLink l = cvLinks.findById(id).orElseGet(() -> MatchCvLink.builder().candidateId(id).build());
                l.setStatus(SyncStatus.PENDING);
                l.setContentHash(null);
                l.setAttempts(0);
                cvLinks.save(l);
                nCv++;
            }
        }
        log.info("cvmatch backfill scope={} jd={} cv={}", scope, nJd, nCv);
        return Map.of("jd", nJd, "cv", nCv);
    }

    // ------------------------------------------------------------------------------------------- noi bo

    private SyncStatus save(MatchCvLink link, SyncStatus status, String error, boolean failed) {
        link.setStatus(status);
        link.setLastError(trim(error));
        link.setAttempts(failed ? link.getAttempts() + 1 : 0);
        cvLinks.save(link);
        if (failed) log.warn("cvmatch sync CV candidate={} that bai (lan {}): {}", link.getCandidateId(),
                link.getAttempts(), error);
        return status;
    }

    private SyncStatus saveJd(MatchJdLink link, SyncStatus status, String error, boolean failed) {
        link.setStatus(status);
        link.setLastError(trim(error));
        link.setAttempts(failed ? link.getAttempts() + 1 : 0);
        jdLinks.save(link);
        if (failed) log.warn("cvmatch sync JD job={} that bai (lan {}): {}", link.getJobId(), link.getAttempts(), error);
        return status;
    }

    private String first(Integer candidateId, String field) {
        return cvData.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field).stream()
                .map(CvData::getValue).filter(v -> v != null && !v.isBlank()).findFirst().orElse("");
    }

    private Object lock(String key) {
        return locks.computeIfAbsent(key, k -> new Object());
    }

    private static String trim(String s) {
        return s == null ? null : (s.length() > 2000 ? s.substring(0, 2000) : s);
    }
}
