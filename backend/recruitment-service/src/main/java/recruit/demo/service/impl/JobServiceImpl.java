package recruit.demo.service.impl;

import recruit.demo.service.*;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.Role;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.JobDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.entity.*;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.*;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

@Service
@RequiredArgsConstructor
public class JobServiceImpl implements JobService {

    private final JobRepository jobRepository;
    private final JobSkillRepository jobSkillRepository;
    private final SkillRepository skillRepository;
    private final RecruiterProfileRepository recruiterProfileRepository;
    private final org.springframework.context.ApplicationEventPublisher events;

    @Transactional(readOnly = true)
    public PageResponse<JobDtos.JobResponse> list(String keyword, String city, String status, Pageable pageable) {
        JobStatus jobStatus = parseStatusOrNull(status);
        if (jobStatus == null && (status == null || status.isBlank())) {
            jobStatus = JobStatus.PUBLISHED;
        }
        Page<Job> page = jobRepository.search(blankToNull(keyword), blankToNull(city), jobStatus, pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
    }

    @Transactional(readOnly = true)
    public JobDtos.JobResponse getById(Integer id) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        return toResponse(job);
    }

    @Transactional
    public JobDtos.JobResponse create(JobDtos.CreateJobRequest request) {
        UserPrincipal principal = SecurityUtils.currentUser();
        RecruiterProfile recruiter = requireRecruiter();

        JobStatus status = request.status() != null ? request.status() : JobStatus.DRAFT;
        Job job = Job.builder()
                .company(recruiter.getCompany())
                .createdById(principal.getId())
                .title(request.title().trim())
                .description(request.description())
                .requirements(blankToNull(request.requirements()))
                .responsibilities(blankToNull(request.responsibilities()))
                .employmentType(request.workType())
                .workLocation(firstNonBlank(request.location(), request.city()))
                .salaryMin(null)
                .salaryMax(null)
                .currency("VND")
                .experienceRequired(request.minYears() != null ? request.minYears() : BigDecimal.ZERO)
                .status(status)
                .postedAt(status == JobStatus.PUBLISHED ? LocalDateTime.now() : null)
                .build();
        parseSalaryText(request.salaryText(), job);
        jobRepository.save(job);
        attachSkills(job, request.requiredSkills(), true);
        attachSkills(job, request.preferredSkills(), false);
        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        return toResponse(job);
    }

    @Transactional
    public JobDtos.JobResponse updateStatus(Integer id, String statusRaw) {
        Job job = jobRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Job not found"));
        ensureOwnsJob(job);

        JobStatus status = parseStatus(statusRaw);
        job.setStatus(status);
        if (status == JobStatus.PUBLISHED && job.getPostedAt() == null) {
            job.setPostedAt(LocalDateTime.now());
        }
        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.JobChanged(job.getId()));
        return toResponse(job);
    }

    @Transactional(readOnly = true)
    public PageResponse<JobDtos.JobResponse> myJobs(Pageable pageable) {
        UserPrincipal principal = SecurityUtils.currentUser();
        Page<Job> page = jobRepository.findByCreatedByIdOrderByCreatedAtDesc(principal.getId(), pageable);
        return PageResponse.toPageResponse(page, this::toResponse);
    }

    private void attachSkills(Job job, List<String> skillNames, boolean required) {
        if (skillNames == null) {
            return;
        }
        for (String name : skillNames) {
            if (name == null || name.isBlank()) {
                continue;
            }
            Skill skill = skillRepository.findByNameIgnoreCase(name.trim())
                    .orElseGet(() -> skillRepository.save(Skill.builder().name(name.trim()).category("General").build()));
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
        boolean hot = job.getPostedAt() != null && job.getPostedAt().isAfter(LocalDateTime.now().minusDays(1));

        return new JobDtos.JobResponse(
                job.getId(),
                job.getTitle(),
                job.getCompany().getName(),
                job.getCompany().getId(),
                location,
                city,
                job.getEmploymentType(),
                deriveLevel(job.getTitle()),
                formatSalaryText(job),
                job.getExperienceRequired() != null ? job.getExperienceRequired() : BigDecimal.ZERO,
                job.getStatus(),
                hot,
                job.getDescription(),
                job.getRequirements(),
                job.getResponsibilities(),
                job.getPostedAt(),
                required,
                preferred
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
        // Keep free-text as description fallback; numeric parse is best-effort for "15 – 22 triệu"
        String normalized = salaryText.toLowerCase(Locale.ROOT).replace(",", "");
        if (normalized.contains("thỏa thuận") || normalized.contains("thoả thuận")) {
            return;
        }
        // store millions as VND if "triệu" present
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
                // leave nulls
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
        if (raw == null || raw.isBlank()) {
            return null;
        }
        return parseStatus(raw);
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private String firstNonBlank(String a, String b) {
        if (a != null && !a.isBlank()) {
            return a.trim();
        }
        if (b != null && !b.isBlank()) {
            return b.trim();
        }
        return null;
    }
}
