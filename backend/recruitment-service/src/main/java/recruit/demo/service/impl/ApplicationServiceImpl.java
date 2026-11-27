package recruit.demo.service.impl;

import recruit.demo.dto.FileLinkDto;
import recruit.demo.storage.ObjectKeys;
import recruit.demo.storage.StorageService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.ApplicationDtos.*;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.ServiceDtos.UserSnapshot;
import recruit.demo.entity.*;
import recruit.demo.enums.ApplicationStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.messaging.NotificationConstants;
import recruit.demo.messaging.OutboxWriter;
import recruit.demo.repository.*;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.ApplicationService;
import recruit.demo.service.CvService;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.util.*;

@Service
@RequiredArgsConstructor
public class ApplicationServiceImpl implements ApplicationService {

    private final IdentityClient identityClient;
    private final StorageService storageService;
    private final JobApplicationRepository applicationRepository;
    private final JobRepository jobRepository;
    private final CandidateProfileRepository candidateProfileRepository;
    private final ApplicationStatusHistoryRepository historyRepository;
    private final ApplicationNoteRepository noteRepository;
    private final CvDataRepository cvDataRepository;
    private final MatchingResultRepository matchingResultRepository;
    private final JobSkillRepository jobSkillRepository;
    private final ObjectMapper objectMapper;
    private final CvDocumentRepository cvDocumentRepository;
    private final ObjectProvider<OutboxWriter> outboxWriter;

    @Override
    @Transactional
    public ApplicationResponse apply(Integer jobId, ApplyRequest request) {
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
                .cvId(resolveApplyCv(candidate, request != null ? request.cvDocumentId() : null))
                .status(ApplicationStatus.SUBMITTED)
                .coverLetter(request != null ? request.coverLetter() : null)
                .build();
        applicationRepository.save(application);

        UserPrincipal principal = SecurityUtils.currentUser();
        historyRepository.save(ApplicationStatusHistory.builder()
                .application(application)
                .fromStatus(null)
                .toStatus(ApplicationStatus.SUBMITTED.name())
                .note(null)
                .actorUserId(principal.getId())
                .actorName("Ứng viên")
                .build());

        return toResponse(application);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<ApplicationResponse> myApplications(Pageable pageable) {
        CandidateProfile candidate = requireCandidate();
        Page<JobApplication> page = applicationRepository.findByCandidateIdOrderByAppliedAtDesc(candidate.getId(), pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<ApplicationResponse> recruiterApplications(Pageable pageable) {
        return recruiterApplications(null, null, null, pageable);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<ApplicationResponse> recruiterApplications(String statusRaw, Integer jobId, Integer minMatchScore, Pageable pageable) {
        UserPrincipal principal = SecurityUtils.currentUser();
        ApplicationStatus status = parseStatusOrNull(statusRaw);
        Page<JobApplication> page = applicationRepository.findForRecruiterFiltered(principal.getId(), status, jobId, pageable);
        PageResponse<ApplicationResponse> res = PageResponse.toPageResponse(page, this::toResponse);
        if (minMatchScore != null && minMatchScore > 0) {
            List<ApplicationResponse> filtered = res.getContent().stream()
                    .filter(a -> a.matchScore() != null && a.matchScore() >= minMatchScore)
                    .toList();
            res.setContent(filtered);
        }
        return res;
    }

    @Override
    @Transactional(readOnly = true)
    public ApplicationDetailResponse getDetail(Integer id) {
        JobApplication app = requireApplication(id);
        boolean isRecruiter = ensureCanAccess(app);
        return toDetailResponse(app, isRecruiter);
    }

    @Override
    @Transactional
    public ApplicationDetailResponse updateStatus(Integer id, String statusRaw, String note) {
        JobApplication app = requireApplication(id);
        ensureRecruiterOwns(app);
        UserPrincipal actor = SecurityUtils.currentUser();
        ApplicationStatus next = parseStatus(statusRaw);
        transitionStatus(app, next, note, actor);
        return toDetailResponse(app, true);
    }

    @Override
    @Transactional
    public List<ApplicationResponse> bulkUpdateStatus(List<Integer> applicationIds, String statusRaw, String note) {
        UserPrincipal actor = SecurityUtils.currentUser();
        ApplicationStatus next = parseStatus(statusRaw);
        List<ApplicationResponse> updated = new ArrayList<>();
        for (Integer id : applicationIds) {
            JobApplication app = requireApplication(id);
            ensureRecruiterOwns(app);
            transitionStatus(app, next, note, actor);
            updated.add(toResponse(app));
        }
        return updated;
    }

    @Override
    @Transactional
    public ApplicationDetailResponse withdraw(Integer id) {
        JobApplication app = requireApplication(id);
        CandidateProfile candidate = requireCandidate();
        if (!app.getCandidate().getId().equals(candidate.getId())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Not your application");
        }
        ApplicationStatus cur = app.getStatus();
        if (cur == ApplicationStatus.HIRED || cur == ApplicationStatus.REJECTED || cur == ApplicationStatus.WITHDRAWN) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Không thể rút đơn đã kết thúc.");
        }
        UserPrincipal principal = SecurityUtils.currentUser();
        app.setStatus(ApplicationStatus.WITHDRAWN);
        applicationRepository.save(app);

        historyRepository.save(ApplicationStatusHistory.builder()
                .application(app)
                .fromStatus(cur.name())
                .toStatus(ApplicationStatus.WITHDRAWN.name())
                .note("Ứng viên tự rút đơn")
                .actorUserId(principal.getId())
                .actorName("Ứng viên")
                .build());
        return toDetailResponse(app, false);
    }

    @Override
    @Transactional
    public ApplicationDetailResponse saveNote(Integer id, int rating, String internalNote) {
        JobApplication app = requireApplication(id);
        ensureRecruiterOwns(app);
        if (rating < 0 || rating > 5) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Điểm đánh giá phải từ 0 đến 5.");
        }
        UserPrincipal actor = SecurityUtils.currentUser();
        ApplicationNote note = noteRepository.findByApplicationId(id)
                .orElseGet(() -> ApplicationNote.builder().application(app).build());
        note.setRating(rating);
        note.setInternalNote(internalNote == null ? "" : internalNote.trim());
        note.setUpdatedBy(actor.getId());
        ApplicationNote saved = noteRepository.save(note);
        return toDetailResponse(app, true, saved);
    }

    @Override
    @Transactional(readOnly = true)
    public List<ApplicationHistoryDto> history(Integer id) {
        JobApplication app = requireApplication(id);
        ensureCanAccess(app);
        return buildHistory(app);
    }

    @Override
    @Transactional(readOnly = true)
    public FileLinkDto loadCvFile(Integer id) {
        JobApplication app = requireApplication(id);
        ensureCanAccess(app);
        Integer candidateId = app.getCandidate().getId();
        String key = cvValue(candidateId, app.getCvId(), CvService.FILE_URL);
        if (key.isBlank()) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Ứng viên chưa tải lên tệp CV.");
        }
        if (!ObjectKeys.isObjectKey(key)) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Tệp CV chưa được chuyển lên kho lưu trữ.");
        }
        String fileName = cvValue(candidateId, app.getCvId(), CvService.FILE_NAME);
        return storageService.presignGet(key, fileName.isBlank() ? "cv-ung-vien-" + app.getId() + ".pdf" : fileName, false);
    }

    private void transitionStatus(JobApplication app, ApplicationStatus next, String note, UserPrincipal actor) {
        ApplicationStatus cur = app.getStatus();
        if (cur == next) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Đơn đã ở trạng thái " + statusLabel(next));
        }
        boolean allowed = switch (cur) {
            case SUBMITTED -> next == ApplicationStatus.REVIEWING || next == ApplicationStatus.INTERVIEW || next == ApplicationStatus.REJECTED;
            case REVIEWING -> next == ApplicationStatus.INTERVIEW || next == ApplicationStatus.HIRED || next == ApplicationStatus.REJECTED;
            case INTERVIEW -> next == ApplicationStatus.HIRED || next == ApplicationStatus.REJECTED;
            case HIRED, REJECTED, WITHDRAWN -> false;
        };
        if (!allowed) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Không thể chuyển trạng thái từ " + statusLabel(cur) + " sang " + statusLabel(next));
        }

        app.setStatus(next);
        applicationRepository.save(app);

        String actorName = actor.getFullName() != null && !actor.getFullName().isBlank()
                ? actor.getFullName()
                : actor.getEmail();
        historyRepository.save(ApplicationStatusHistory.builder()
                .application(app)
                .fromStatus(cur.name())
                .toStatus(next.name())
                .note(note == null || note.isBlank() ? null : note.trim())
                .actorUserId(actor.getId())
                .actorName(actorName)
                .build());

        if (next == ApplicationStatus.INTERVIEW || next == ApplicationStatus.REVIEWING
                || next == ApplicationStatus.HIRED || next == ApplicationStatus.REJECTED) {
            boolean interview = next == ApplicationStatus.INTERVIEW;
            NotificationOutbox.publish(
                    outboxWriter,
                    NotificationConstants.RK_APPLICATION_STATUS_CHANGED,
                    interview ? NotificationType.INTERVIEW_INVITE : NotificationType.APPLICATION_STATUS,
                    List.of(app.getCandidate().getUserId()),
                    interview ? "Lời mời phỏng vấn" : "Đơn ứng tuyển " + statusLabel(next),
                    app.getJob().getTitle() + " · " + app.getJob().getCompany().getName(),
                    "/candidate/applications",
                    Map.of("applicationId", app.getId(), "status", next.name()));
        }
    }

    private ApplicationResponse toResponse(JobApplication app) {
        Integer score = matchingResultRepository
                .findFirstByJobIdAndCandidateIdOrderByCreatedAtDesc(app.getJob().getId(), app.getCandidate().getId())
                .map(m -> toPercent(m.getOverallScore()))
                .orElse(null);

        return new ApplicationResponse(
                app.getId(),
                app.getJob().getId(),
                app.getJob().getTitle(),
                app.getJob().getCompany().getName(),
                app.getCandidate().getId(),
                resolveCandidateName(app.getCandidate().getUserId()),
                app.getCvId(),
                app.getStatus(),
                app.getCoverLetter(),
                app.getAppliedAt(),
                score
        );
    }

    private ApplicationDetailResponse toDetailResponse(JobApplication app, boolean isRecruiter) {
        ApplicationNote noteEntity = isRecruiter
                ? noteRepository.findByApplicationId(app.getId()).orElse(null)
                : null;
        return toDetailResponse(app, isRecruiter, noteEntity);
    }

    private ApplicationDetailResponse toDetailResponse(JobApplication app, boolean isRecruiter, ApplicationNote noteEntity) {
        CandidateProfile candidate = app.getCandidate();
        UserSnapshot snap = resolveUserSnapshot(candidate.getUserId());
        String candidateName = snap != null && snap.fullName() != null ? snap.fullName() : "Ứng viên #" + candidate.getId();

        String cvFileName = cvValue(candidate.getId(), app.getCvId(), CvService.FILE_NAME);
        String cvFileUrl = cvValue(candidate.getId(), app.getCvId(), CvService.FILE_URL);

        MatchingResult match = matchingResultRepository
                .findFirstByJobIdAndCandidateIdOrderByCreatedAtDesc(app.getJob().getId(), candidate.getId())
                .orElse(null);

        ApplicationCvDto cvDto = buildCvDto(candidate, app.getCvId(), snap, app.getJob(), match);
        ApplicationMatchDto matchDto = buildMatchDto(match);
        List<ApplicationHistoryDto> historyList = buildHistory(app);

        return new ApplicationDetailResponse(
                app.getId(),
                app.getJob().getId(),
                app.getJob().getTitle(),
                app.getJob().getCompany().getName(),
                candidate.getId(),
                candidateName,
                app.getCvId(),
                cvFileName.isBlank() ? null : cvFileName,
                !cvFileUrl.isBlank(),
                app.getStatus(),
                app.getCoverLetter(),
                app.getAppliedAt(),
                noteEntity != null ? noteEntity.getRating() : 0,
                noteEntity != null ? noteEntity.getInternalNote() : null,
                cvDto,
                matchDto,
                historyList
        );
    }

    private ApplicationCvDto buildCvDto(CandidateProfile candidate, Integer cvId, UserSnapshot snap, Job job,
                                       MatchingResult match) {
        String profileJson = cvValue(candidate.getId(), cvId, CvService.PROFILE_JSON);
        CandidateProfileDto parsed = null;
        if (!profileJson.isBlank()) {
            try {
                parsed = objectMapper.readValue(profileJson, CandidateProfileDto.class);
            } catch (Exception ignored) {
            }
        }

        String roleTitle = candidate.getHeadline() != null && !candidate.getHeadline().isBlank()
                ? candidate.getHeadline()
                : job.getTitle();
        String yearsLabel = candidate.getYearsOfExperience() != null
                ? candidate.getYearsOfExperience().stripTrailingZeros().toPlainString() + " năm kinh nghiệm"
                : "Chưa cập nhật";
        String email = snap != null && snap.email() != null ? snap.email() : "";
        String phone = snap != null && snap.phone() != null ? snap.phone() : "";
        String summary = candidate.getSummary() != null ? candidate.getSummary() : "";

        List<ApplicationExperienceItem> exps = new ArrayList<>();
        String education = "";
        List<String> allSkills = new ArrayList<>();

        if (parsed != null) {
            if (parsed.getPersonal_info() != null) {
                if (email.isBlank() && parsed.getPersonal_info().getEmail() != null) email = parsed.getPersonal_info().getEmail();
                if (phone.isBlank() && parsed.getPersonal_info().getPhone() != null) phone = parsed.getPersonal_info().getPhone();
            }
            if (summary.isBlank() && parsed.getObjective() != null) summary = parsed.getObjective();
            if (parsed.getExperience() != null) {
                for (var we : parsed.getExperience()) {
                    String title = (we.getJob_title() != null ? we.getJob_title() : "Vị trí")
                            + (we.getCompany() != null && !we.getCompany().isBlank() ? " · " + we.getCompany() : "");
                    String period = (we.getStart_date() != null ? we.getStart_date() : "")
                            + (we.getEnd_date() != null ? " – " + we.getEnd_date() : " – nay");
                    String desc = we.getDescription() != null ? String.join("; ", we.getDescription()) : "";
                    exps.add(new ApplicationExperienceItem(title, we.getCompany(), period.trim(), desc));
                }
            }
            if (parsed.getEducation() != null && !parsed.getEducation().isEmpty()) {
                var ed = parsed.getEducation().get(0);
                education = String.join(" · ", Arrays.stream(new String[]{
                        ed.getSchool(), ed.getMajor(),
                        ed.getStart_year() != null || ed.getEnd_year() != null
                                ? (ed.getStart_year() != null ? ed.getStart_year() : "") + " – " + (ed.getEnd_year() != null ? ed.getEnd_year() : "")
                                : null
                }).filter(s -> s != null && !s.isBlank()).toList());
            }
            if (parsed.getSkills() != null) {
                allSkills.addAll(parsed.getSkills());
            }
        }

        if (exps.isEmpty()) {
            for (String line : cvLines(candidate.getId(), cvId, "Kinh nghiệm")) {
                exps.add(new ApplicationExperienceItem(line, "", "", ""));
            }
        }
        if (education.isBlank()) {
            List<String> eds = cvLines(candidate.getId(), cvId, "Học vấn");
            if (!eds.isEmpty()) education = String.join(" · ", eds);
        }
        if (allSkills.isEmpty()) {
            for (String line : cvLines(candidate.getId(), cvId, "Kỹ năng")) {
                for (String token : line.split("[,;\\n]+")) {
                    if (!token.isBlank()) allSkills.add(token.trim());
                }
            }
        }

        List<String> matched = match != null && match.getMatchedSkills() != null ? match.getMatchedSkills() : List.of();
        Set<String> matchedLower = new HashSet<>();
        matched.forEach(s -> matchedLower.add(s.toLowerCase(Locale.ROOT)));
        if (matched.isEmpty()) {
            Set<String> reqLower = new HashSet<>();
            jobSkillRepository.findByJobId(job.getId()).forEach(js -> reqLower.add(js.getSkill().getName().toLowerCase(Locale.ROOT)));
            List<String> computedMatched = new ArrayList<>();
            for (String s : allSkills) {
                if (reqLower.contains(s.toLowerCase(Locale.ROOT))) {
                    computedMatched.add(s);
                    matchedLower.add(s.toLowerCase(Locale.ROOT));
                }
            }
            matched = computedMatched;
        }
        List<String> other = allSkills.stream()
                .filter(s -> !matchedLower.contains(s.toLowerCase(Locale.ROOT)))
                .distinct()
                .toList();

        return new ApplicationCvDto(roleTitle, yearsLabel, email, phone, summary, exps, education, matched, other);
    }

    private ApplicationMatchDto buildMatchDto(MatchingResult match) {
        if (match == null) {
            return null;
        }
        int overall = toPercent(match.getOverallScore());
        int semantic = toPercent(match.getSemanticScore());
        int skills = toPercent(match.getSkillsScore());
        int exp = toPercent(match.getExperienceScore());
        return new ApplicationMatchDto(
                overall,
                List.of(
                        new MatchBreakdownItem("Ngữ nghĩa / Chức danh", semantic),
                        new MatchBreakdownItem("Kỹ năng", skills),
                        new MatchBreakdownItem("Kinh nghiệm", exp)
                ),
                match.getMissingSkills() != null ? match.getMissingSkills() : List.of()
        );
    }

    private List<ApplicationHistoryDto> buildHistory(JobApplication app) {
        List<ApplicationStatusHistory> rows = historyRepository.findByApplicationIdOrderByCreatedAtDescIdDesc(app.getId());
        if (rows.isEmpty()) {
            return List.of(new ApplicationHistoryDto(
                    0,
                    null,
                    app.getStatus().name(),
                    statusLabel(app.getStatus()),
                    app.getAppliedAt(),
                    "Ứng viên",
                    null
            ));
        }
        return rows.stream()
                .map(h -> new ApplicationHistoryDto(
                        h.getId(),
                        h.getFromStatus(),
                        h.getToStatus(),
                        statusLabelRaw(h.getToStatus()),
                        h.getCreatedAt(),
                        h.getActorName() != null ? h.getActorName() : "Hệ thống",
                        h.getNote()
                ))
                .toList();
    }

    private boolean ensureCanAccess(JobApplication app) {
        UserPrincipal principal = SecurityUtils.currentUser();
        if (app.getJob().getCreatedById().equals(principal.getId())) {
            return true;
        }
        if (app.getCandidate().getUserId().equals(principal.getId())) {
            return false;
        }
        throw new ApiException(HttpStatus.FORBIDDEN, "Bạn không có quyền truy cập đơn ứng tuyển này.");
    }

    private void ensureRecruiterOwns(JobApplication app) {
        UserPrincipal principal = SecurityUtils.currentUser();
        if (!app.getJob().getCreatedById().equals(principal.getId())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Not your job application");
        }
    }

    private JobApplication requireApplication(Integer id) {
        return applicationRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Application not found"));
    }

    private CandidateProfile requireCandidate() {
        UserPrincipal principal = SecurityUtils.currentUser();
        return candidateProfileRepository.findByUserId(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Candidate profile not found"));
    }

    private UserSnapshot resolveUserSnapshot(Integer userId) {
        try {
            return identityClient.get(userId);
        } catch (Exception ex) {
            return null;
        }
    }

    private String resolveCandidateName(Integer userId) {
        UserSnapshot snap = resolveUserSnapshot(userId);
        return snap != null && snap.fullName() != null ? snap.fullName() : "Ứng viên #" + userId;
    }

    /**
     * CV mà ứng viên chọn khi ứng tuyển. Bỏ trống thì dùng CV chính (chưa có CV thì null, như trước).
     * CV phải thuộc ứng viên và đã trích xuất xong.
     */
    private Integer resolveApplyCv(CandidateProfile candidate, Integer cvDocumentId) {
        if (cvDocumentId == null) {
            return cvDocumentRepository.findFirstByCandidateIdAndMainTrue(candidate.getId())
                    .map(CvDocument::getId).orElse(null);
        }
        if (cvDocumentRepository.findByIdAndCandidateId(cvDocumentId, candidate.getId()).isEmpty()
                || !"COMPLETED".equals(cvValue(candidate.getId(), cvDocumentId, CvService.PARSING_STATUS))) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "CV đã chọn không hợp lệ");
        }
        return cvDocumentId;
    }

    /** cvId = CV gắn với đơn; null (đơn cũ) thì đọc CV chính của ứng viên. */
    private List<CvData> cvRows(Integer candidateId, Integer cvId, String field) {
        return cvId != null
                ? cvDataRepository.findByCvIdAndFieldOrderByIdAsc(cvId, field)
                : cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field);
    }

    private String cvValue(Integer candidateId, Integer cvId, String field) {
        return cvRows(candidateId, cvId, field).stream()
                .map(CvData::getValue)
                .filter(v -> v != null && !v.isBlank())
                .findFirst()
                .orElse("");
    }

    private List<String> cvLines(Integer candidateId, Integer cvId, String field) {
        return cvRows(candidateId, cvId, field).stream()
                .map(CvData::getValue)
                .filter(v -> v != null && !v.isBlank())
                .map(String::trim)
                .toList();
    }

    private int toPercent(BigDecimal score) {
        if (score == null) return 0;
        return Math.min(100, Math.max(0, Math.round(score.multiply(BigDecimal.valueOf(100)).floatValue())));
    }

    private ApplicationStatus parseStatus(String raw) {
        try {
            return ApplicationStatus.valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Trạng thái đơn không hợp lệ.");
        }
    }

    private ApplicationStatus parseStatusOrNull(String raw) {
        if (raw == null || raw.isBlank() || "ALL".equalsIgnoreCase(raw.trim())) {
            return null;
        }
        return parseStatus(raw);
    }

    private String statusLabel(ApplicationStatus s) {
        return switch (s) {
            case SUBMITTED -> "Đã nộp";
            case REVIEWING -> "Đang xem xét";
            case INTERVIEW -> "Mời phỏng vấn";
            case HIRED -> "Trúng tuyển";
            case REJECTED -> "Từ chối";
            case WITHDRAWN -> "Đã rút";
        };
    }

    private String statusLabelRaw(String raw) {
        try {
            return statusLabel(ApplicationStatus.valueOf(raw));
        } catch (Exception ex) {
            return raw;
        }
    }
}
