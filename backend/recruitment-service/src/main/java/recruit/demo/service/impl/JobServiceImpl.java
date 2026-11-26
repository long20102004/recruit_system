package recruit.demo.service.impl;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.entity.*;
import recruit.demo.enums.CompanyStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.JobService;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.time.LocalDateTime;
import java.util.*;

@Service
@RequiredArgsConstructor
public class JobServiceImpl implements JobService {

    private final JobRepository jobRepository;
    private final JobSkillRepository jobSkillRepository;
    private final SkillRepository skillRepository;
    private final RecruiterProfileRepository recruiterProfileRepository;
    private final JobApplicationRepository applicationRepository;
    private final IdentityClient identityClient;
    private final org.springframework.context.ApplicationEventPublisher events;

    @Override
    @Transactional(readOnly = true)
    public PageResponse<JobDtos.JobResponse> list(String keyword, String city, String status, Pageable pageable) {
        return list(keyword, city, status, null, pageable);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<JobDtos.JobResponse> list(String keyword, String city, String status, BigDecimal minSalary, Pageable pageable) {
        JobStatus jobStatus = parseStatusOrNull(status);
        if (jobStatus == null && (status == null || status.isBlank())) {
            jobStatus = JobStatus.PUBLISHED;
        }
        Page<Job> page = jobRepository.search(blankToNull(keyword), blankToNull(city), jobStatus, minSalary, pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
    }

    @Override
    @Transactional(readOnly = true)
    public JobDtos.JobResponse getById(Integer id) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        return toResponse(job);
    }

    @Override
    @Transactional
    public JobDtos.JobResponse create(JobDtos.CreateJobRequest request) {
        UserPrincipal principal = SecurityUtils.currentUser();
        RecruiterProfile recruiter = requireRecruiter();
        Company company = recruiter.getCompany();

        JobStatus status = request.status() != null ? request.status() : JobStatus.DRAFT;
        if (status == JobStatus.PUBLISHED) {
            ensureCompanyActiveForPublish(company);
        }

        Job job = Job.builder()
                .company(company)
                .createdById(principal.getId())
                .title(request.title().trim())
                .description(request.description())
                .requirements(blankToNull(request.requirements()))
                .responsibilities(blankToNull(request.responsibilities()))
                .employmentType(request.workType())
                .workLocation(firstNonBlank(request.location(), request.city()))
                .level(blankToNull(request.level()))
                .salaryMin(request.salaryMin())
                .salaryMax(request.salaryMax())
                .currency(firstNonBlank(request.currency(), "VND"))
                .experienceRequired(request.minYears() != null ? request.minYears() : BigDecimal.ZERO)
                .headcount(request.headcount())
                .benefits(blankToNull(request.benefits()))
                .hot(Boolean.TRUE.equals(request.hot()))
                .defaultInterviewQuestions(request.defaultInterviewQuestions() != null ? request.defaultInterviewQuestions() : 5)
                .deadline(request.deadline())
                .status(status)
                .postedAt(status == JobStatus.PUBLISHED ? LocalDateTime.now() : null)
                .build();
        if (job.getSalaryMin() == null && job.getSalaryMax() == null) {
            parseSalaryText(request.salaryText(), job);
        }
        jobRepository.save(job);
        attachSkills(job, request.requiredSkills(), true);
        attachSkills(job, request.preferredSkills(), false);
        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        return toResponse(job);
    }

    @Override
    @Transactional
    public JobDtos.JobResponse update(Integer id, JobDtos.UpdateJobRequest request) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        ensureOwnsJob(job);
        if (job.getStatus() == JobStatus.LOCKED) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tin đang bị admin khoá, không thể chỉnh sửa.");
        }

        JobStatus nextStatus = request.status() != null ? request.status() : job.getStatus();
        if (nextStatus == JobStatus.PUBLISHED) {
            ensureCompanyActiveForPublish(job.getCompany());
        }

        job.setTitle(request.title().trim());
        job.setDescription(request.description());
        job.setRequirements(blankToNull(request.requirements()));
        job.setResponsibilities(blankToNull(request.responsibilities()));
        job.setEmploymentType(request.workType());
        job.setWorkLocation(firstNonBlank(request.location(), request.city()));
        job.setLevel(blankToNull(request.level()));
        job.setExperienceRequired(request.minYears() != null ? request.minYears() : BigDecimal.ZERO);
        if (request.headcount() != null) job.setHeadcount(request.headcount());
        job.setBenefits(blankToNull(request.benefits()));
        if (request.hot() != null) job.setHot(request.hot());
        if (request.defaultInterviewQuestions() != null) {
            job.setDefaultInterviewQuestions(request.defaultInterviewQuestions());
        }
        if (request.deadline() != null) {
            job.setDeadline(request.deadline());
        }
        if (request.salaryMin() != null || request.salaryMax() != null) {
            job.setSalaryMin(request.salaryMin());
            job.setSalaryMax(request.salaryMax());
            if (!isBlank(request.currency())) job.setCurrency(request.currency().trim());
        } else if (request.salaryText() != null) {
            job.setSalaryMin(null);
            job.setSalaryMax(null);
            parseSalaryText(request.salaryText(), job);
        }

        if (nextStatus != JobStatus.LOCKED) {
            job.setStatus(nextStatus);
            if (nextStatus == JobStatus.PUBLISHED && job.getPostedAt() == null) {
                job.setPostedAt(LocalDateTime.now());
            }
        }
        jobRepository.save(job);

        if (request.requiredSkills() != null || request.preferredSkills() != null) {
            jobSkillRepository.deleteByJobId(job.getId());
            jobSkillRepository.flush();
            attachSkills(job, request.requiredSkills(), true);
            attachSkills(job, request.preferredSkills(), false);
        }

        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        return toResponse(job);
    }

    @Override
    @Transactional
    public void delete(Integer id) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        ensureOwnsJob(job);
        if (job.getStatus() != JobStatus.DRAFT) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Chỉ có thể xoá tin ở trạng thái Nháp (DRAFT).");
        }
        if (applicationRepository.countByJobId(id) > 0) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Không thể xoá tin đã có ứng viên nộp đơn.");
        }
        jobRepository.delete(job);
    }

    @Override
    @Transactional
    public JobDtos.JobResponse updateStatus(Integer id, String statusRaw) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        ensureOwnsJob(job);
        if (job.getStatus() == JobStatus.LOCKED) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tin đang bị khoá bởi quản trị viên, không thể tự mở lại.");
        }

        JobStatus status = parseStatus(statusRaw);
        if (status == JobStatus.LOCKED) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Chỉ admin mới có quyền khoá tin.");
        }
        if (status == JobStatus.PUBLISHED) {
            ensureCompanyActiveForPublish(job.getCompany());
        }
        job.setStatus(status);
        if (status == JobStatus.PUBLISHED && job.getPostedAt() == null) {
            job.setPostedAt(LocalDateTime.now());
        }
        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        return toResponse(job);
    }

    @Override
    @Transactional
    public JobDtos.JobResponse renew(Integer id, LocalDateTime newDeadline) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        ensureOwnsJob(job);
        if (job.getStatus() == JobStatus.LOCKED) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tin đang bị khoá, không thể gia hạn.");
        }
        ensureCompanyActiveForPublish(job.getCompany());
        LocalDateTime targetDeadline = newDeadline != null ? newDeadline : LocalDateTime.now().plusDays(30);
        if (targetDeadline.isBefore(LocalDateTime.now())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Hạn nộp mới phải ở tương lai.");
        }
        job.setDeadline(targetDeadline);
        if (job.getStatus() == JobStatus.EXPIRED || job.getStatus() == JobStatus.CLOSED || job.getStatus() == JobStatus.DRAFT) {
            job.setStatus(JobStatus.PUBLISHED);
            if (job.getPostedAt() == null) {
                job.setPostedAt(LocalDateTime.now());
            }
        }
        jobRepository.save(job);
        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        return toResponse(job);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<JobDtos.JobResponse> myJobs(Pageable pageable) {
        UserPrincipal principal = SecurityUtils.currentUser();
        Page<Job> page = jobRepository.findByCreatedByIdOrderByCreatedAtDesc(principal.getId(), pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<JobDtos.JobResponse> adminList(String status, Integer companyId, String keyword, Pageable pageable) {
        JobStatus parsed = parseStatusOrNull(status);
        Page<Job> page = jobRepository.adminSearch(parsed, companyId, blankToNull(keyword), pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
    }

    @Override
    @Transactional(readOnly = true)
    public Map<Integer, JobDtos.JobLockStateDto> adminLockStates() {
        Map<Integer, JobDtos.JobLockStateDto> out = new LinkedHashMap<>();
        for (Job j : jobRepository.findByStatus(JobStatus.LOCKED)) {
            out.put(j.getId(), new JobDtos.JobLockStateDto(
                    j.getId(),
                    true,
                    firstNonBlank(j.getLockReason(), "Vi phạm quy định"),
                    orEmpty(j.getLockNote()),
                    j.getLockedAt()
            ));
        }
        return out;
    }

    @Override
    @Transactional
    public JobDtos.JobLockStateDto lockJob(Integer id, String reason, String note) {
        if (isBlank(reason)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng chọn lý do khoá tin.");
        }
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        UserPrincipal actor = SecurityUtils.currentUser();

        job.setStatus(JobStatus.LOCKED);
        job.setLockReason(reason.trim());
        job.setLockNote(blankToNull(note));
        job.setLockedAt(LocalDateTime.now());
        job.setLockedBy(actor.getId());
        jobRepository.save(job);

        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        identityClient.recordAuditLog("LOCK_JOB", "Khoá tin", "badge b-danger",
                job.getTitle(), actor.getId(), actor.getEmail());

        return new JobDtos.JobLockStateDto(job.getId(), true, job.getLockReason(),
                orEmpty(job.getLockNote()), job.getLockedAt());
    }

    @Override
    @Transactional
    public void unlockJob(Integer id) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        UserPrincipal actor = SecurityUtils.currentUser();

        JobStatus restored = (job.getDeadline() != null && job.getDeadline().isBefore(LocalDateTime.now()))
                ? JobStatus.EXPIRED
                : JobStatus.PUBLISHED;
        job.setStatus(restored);
        job.setLockReason(null);
        job.setLockNote(null);
        job.setLockedAt(null);
        job.setLockedBy(null);
        jobRepository.save(job);

        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        identityClient.recordAuditLog("UNLOCK_JOB", "Mở khoá tin", "badge b-ok",
                job.getTitle(), actor.getId(), actor.getEmail());
    }

    private void ensureCompanyActiveForPublish(Company company) {
        if (company.getStatus() != CompanyStatus.ACTIVE) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Công ty chưa được duyệt hoạt động (trạng thái hiện tại: " + company.getStatus() + "). Chỉ có thể lưu tin nháp.");
        }
    }

    private void attachSkills(Job job, List<String> skillNames, boolean required) {
        if (skillNames == null) {
            return;
        }
        Set<String> seen = new HashSet<>();
        for (String name : skillNames) {
            if (name == null || name.isBlank()) {
                continue;
            }
            String clean = name.trim();
            if (!seen.add(clean.toLowerCase(Locale.ROOT))) {
                continue;
            }
            Skill skill = skillRepository.findByNameIgnoreCase(clean)
                    .orElseGet(() -> skillRepository.save(Skill.builder().name(clean).category("General").build()));
            jobSkillRepository.save(JobSkill.builder().job(job).skill(skill).required(required).build());
        }
    }

    private JobDtos.JobResponse toResponse(Job job) {
        List<JobSkill> skills = jobSkillRepository.findByJobId(job.getId());
        List<String> required = new ArrayList<>();
        List<String> preferred = new ArrayList<>();
        for (JobSkill js : skills) {
            if (js.isRequired()) {
                required.add(js.getSkill().getName());
            } else {
                preferred.add(js.getSkill().getName());
            }
        }

        String location = job.getWorkLocation();
        String city = deriveCity(location);
        boolean hot = job.isHot() || (job.getPostedAt() != null && job.getPostedAt().isAfter(LocalDateTime.now().minusDays(1)));
        String level = firstNonBlank(job.getLevel(), deriveLevel(job.getTitle()));
        long applicantsCount = applicationRepository.countByJobId(job.getId());

        return new JobDtos.JobResponse(
                job.getId(),
                job.getTitle(),
                job.getCompany().getName(),
                job.getCompany().getId(),
                location,
                city,
                job.getEmploymentType(),
                level,
                formatSalaryText(job),
                job.getExperienceRequired() != null ? job.getExperienceRequired() : BigDecimal.ZERO,
                job.getStatus(),
                hot,
                job.getDescription(),
                job.getRequirements(),
                job.getResponsibilities(),
                job.getPostedAt(),
                required,
                preferred,
                job.getSalaryMin(),
                job.getSalaryMax(),
                job.getCurrency(),
                job.getHeadcount(),
                job.getBenefits(),
                job.getDeadline(),
                job.getDefaultInterviewQuestions(),
                job.getLockReason(),
                job.getLockNote(),
                job.getLockedAt(),
                applicantsCount,
                job.getCreatedById()
        );
    }

    private String formatSalaryText(Job job) {
        if (job.getSalaryMin() == null && job.getSalaryMax() == null) {
            return "Thỏa thuận";
        }
        DecimalFormatSymbols symbols = new DecimalFormatSymbols(Locale.US);
        DecimalFormat df = new DecimalFormat("#,###", symbols);
        String currency = job.getCurrency() != null ? job.getCurrency() : "VND";
        if (job.getSalaryMin() != null && job.getSalaryMax() != null) {
            return df.format(job.getSalaryMin()) + " – " + df.format(job.getSalaryMax()) + " " + currency;
        }
        if (job.getSalaryMin() != null) {
            return "Từ " + df.format(job.getSalaryMin()) + " " + currency;
        }
        return "Đến " + df.format(job.getSalaryMax()) + " " + currency;
    }

    private void parseSalaryText(String salaryText, Job job) {
        if (salaryText == null || salaryText.isBlank()) {
            return;
        }
        String normalized = salaryText.toLowerCase(Locale.ROOT).replace(",", "");
        if (normalized.contains("thỏa thuận") || normalized.contains("thoả thuận")) {
            return;
        }
        if (normalized.contains("triệu")) {
            String digits = normalized.replaceAll("[^0-9.\\-–]", " ").trim();
            String[] parts = digits.split("[\\-–]+");
            try {
                if (parts.length >= 1 && !parts[0].isBlank()) {
                    job.setSalaryMin(new BigDecimal(parts[0].trim()).multiply(BigDecimal.valueOf(1_000_000))
                            .setScale(2, RoundingMode.HALF_UP));
                }
                if (parts.length >= 2 && !parts[1].isBlank()) {
                    job.setSalaryMax(new BigDecimal(parts[1].trim()).multiply(BigDecimal.valueOf(1_000_000))
                            .setScale(2, RoundingMode.HALF_UP));
                }
            } catch (NumberFormatException ignored) {
            }
        }
    }

    private String deriveCity(String workLocation) {
        if (workLocation == null || workLocation.isBlank()) {
            return null;
        }
        String loc = workLocation.toLowerCase(Locale.ROOT);
        if (loc.contains("hà nội") || loc.contains("ha noi")) {
            return "Hà Nội";
        }
        if (loc.contains("hồ chí minh") || loc.contains("hcm") || loc.contains("tp.hcm") || loc.contains("sài gòn")) {
            return "TP. Hồ Chí Minh";
        }
        if (loc.contains("đà nẵng") || loc.contains("da nang")) {
            return "Đà Nẵng";
        }
        if (loc.contains("remote")) {
            return "Remote";
        }
        return workLocation;
    }

    private String deriveLevel(String title) {
        if (title == null) {
            return null;
        }
        String t = title.toLowerCase(Locale.ROOT);
        if (t.contains("intern") || t.contains("thực tập")) {
            return "Intern";
        }
        if (t.contains("junior") || t.contains("fresher")) {
            return "Junior";
        }
        if (t.contains("senior") || t.contains("lead")) {
            return "Senior";
        }
        if (t.contains("mid")) {
            return "Mid";
        }
        return null;
    }

    private RecruiterProfile requireRecruiter() {
        UserPrincipal principal = SecurityUtils.currentUser();
        return recruiterProfileRepository.findFirstByUserIdOrderByCreatedAtAsc(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Recruiter profile not found"));
    }

    private void ensureOwnsJob(Job job) {
        UserPrincipal principal = SecurityUtils.currentUser();
        if (!job.getCreatedById().equals(principal.getId())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Not your job");
        }
    }

    private JobStatus parseStatus(String raw) {
        try {
            return JobStatus.valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Invalid job status");
        }
    }

    private JobStatus parseStatusOrNull(String raw) {
        if (raw == null || raw.isBlank() || "ALL".equalsIgnoreCase(raw.trim())) {
            return null;
        }
        return parseStatus(raw);
    }

    private boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    private String blankToNull(String value) {
        return isBlank(value) ? null : value.trim();
    }

    private String orEmpty(String value) {
        return value == null ? "" : value;
    }

    private String firstNonBlank(String a, String b) {
        if (!isBlank(a)) {
            return a.trim();
        }
        if (!isBlank(b)) {
            return b.trim();
        }
        return null;
    }
}
