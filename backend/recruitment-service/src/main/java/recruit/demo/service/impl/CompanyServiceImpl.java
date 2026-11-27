package recruit.demo.service.impl;

import recruit.demo.dto.FileLinkDto;
import recruit.demo.storage.ObjectKeys;
import recruit.demo.storage.StorageService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.CompanyDtos.*;
import recruit.demo.entity.Company;
import recruit.demo.entity.CompanyFollower;
import recruit.demo.entity.RecruiterProfile;
import recruit.demo.enums.CompanyStatus;
import recruit.demo.enums.JobStatus;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.messaging.NotificationConstants;
import recruit.demo.messaging.OutboxWriter;
import recruit.demo.repository.CompanyFollowerRepository;
import recruit.demo.repository.CompanyRepository;
import recruit.demo.repository.JobRepository;
import recruit.demo.repository.RecruiterProfileRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.CompanyService;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.*;

@Service
@RequiredArgsConstructor
public class CompanyServiceImpl implements CompanyService {

    private final CompanyRepository companyRepository;
    private final CompanyFollowerRepository followerRepository;
    private final RecruiterProfileRepository recruiterProfileRepository;
    private final JobRepository jobRepository;
    private final IdentityClient identityClient;
    private final StorageService storageService;
    private final ObjectProvider<OutboxWriter> outboxWriter;

    private static final java.util.Set<String> IMAGE_TYPES = java.util.Set.of("image/png", "image/jpeg", "image/webp");
    private static final long MAX_IMAGE_BYTES = 5L * 1024 * 1024;

    @Override
    @Transactional(readOnly = true)
    public List<CompanyDto> listPublic(String q, String city, String industry, String sort) {
        List<Company> list = companyRepository.search(
                CompanyStatus.ACTIVE,
                blankToNull(city),
                blankToNull(industry),
                blankToNull(q));
        Integer currentUserId = optionalUserId();
        List<CompanyDto> dtos = new ArrayList<>(list.stream()
                .map(c -> toDto(c, currentUserId))
                .toList());

        String sortKey = sort == null ? "jobs" : sort.trim().toLowerCase(Locale.ROOT);
        switch (sortKey) {
            case "newest" -> dtos.sort(Comparator.comparing(CompanyDto::submittedAt, Comparator.nullsLast(Comparator.reverseOrder())));
            case "name" -> dtos.sort(Comparator.comparing(CompanyDto::name, String.CASE_INSENSITIVE_ORDER));
            default -> dtos.sort(Comparator.comparingLong(CompanyDto::openJobsCount).reversed()
                    .thenComparing(CompanyDto::name, String.CASE_INSENSITIVE_ORDER));
        }
        return dtos;
    }

    @Override
    @Transactional(readOnly = true)
    public CompanyDto getPublic(Integer id) {
        Company c = requireCompany(id);
        if (c.getStatus() != CompanyStatus.ACTIVE) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy thông tin công ty.");
        }
        return toDto(c, optionalUserId());
    }

    @Override
    @Transactional
    public FollowResponse follow(Integer companyId) {
        UserPrincipal principal = SecurityUtils.currentUser();
        Company company = requireCompany(companyId);
        if (company.getStatus() != CompanyStatus.ACTIVE) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Chỉ có thể theo dõi công ty đang hoạt động.");
        }
        if (!followerRepository.existsByCompanyIdAndUserId(companyId, principal.getId())) {
            followerRepository.save(CompanyFollower.builder()
                    .company(company)
                    .userId(principal.getId())
                    .build());
        }
        return new FollowResponse(companyId, true, followerRepository.countByCompanyId(companyId));
    }

    @Override
    @Transactional
    public FollowResponse unfollow(Integer companyId) {
        UserPrincipal principal = SecurityUtils.currentUser();
        requireCompany(companyId);
        followerRepository.findByCompanyIdAndUserId(companyId, principal.getId())
                .ifPresent(followerRepository::delete);
        return new FollowResponse(companyId, false, followerRepository.countByCompanyId(companyId));
    }

    @Override
    @Transactional(readOnly = true)
    public RecruiterCompanyProfileDto getMyCompany() {
        Company c = requireRecruiterCompany();
        return toRecruiterProfileDto(c);
    }

    @Override
    @Transactional
    public RecruiterCompanyProfileDto saveDraft(CompanyRegistrationRequest request) {
        if (request == null || isBlank(request.name())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng nhập tên công ty trước khi lưu nháp.");
        }
        Company c = requireRecruiterCompany();
        applyRegistrationFields(c, request);
        if (c.getStatus() == CompanyStatus.ACTIVE && isBlank(c.getTaxCode())) {
            c.setStatus(CompanyStatus.DRAFT);
        }
        companyRepository.save(c);
        return toRecruiterProfileDto(c);
    }

    @Override
    @Transactional
    public RecruiterCompanyProfileDto submitRegistration(CompanyRegistrationRequest request) {
        if (request == null
                || isBlank(request.name())
                || isBlank(request.taxCode())
                || isBlank(request.headquarters())
                || isBlank(request.contactEmail())
                || isBlank(request.contactPhone())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng điền đầy đủ các trường bắt buộc (*).");
        }
        Company c = requireRecruiterCompany();
        String licenseName = !isBlank(request.licenseFileName()) ? request.licenseFileName().trim() : c.getLicenseFileName();
        if (isBlank(licenseName)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng chọn tệp Giấy phép kinh doanh.");
        }
        if (!Boolean.TRUE.equals(request.confirmed())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng xác nhận thông tin và quyền đại diện công ty.");
        }

        UserPrincipal principal = SecurityUtils.currentUser();
        applyRegistrationFields(c, request);
        c.setLicenseFileName(licenseName);
        c.setConfirmed(true);
        c.setStatus(CompanyStatus.PENDING);
        c.setSubmittedAt(LocalDateTime.now());
        c.setRejectReason(null);
        c.setSubmittedByUserId(principal.getId());
        c.setSubmittedByLabel(formatActorLabel(principal));
        companyRepository.save(c);
        return toRecruiterProfileDto(c);
    }

    @Override
    @Transactional
    public RecruiterCompanyProfileDto updateProfile(CompanyProfileUpdateRequest request) {
        if (request == null || isBlank(request.displayName())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tên hiển thị công ty không được để trống.");
        }
        Company c = requireRecruiterCompany();
        if (c.getStatus() == CompanyStatus.LOCKED) {
            throw new ApiException(HttpStatus.FORBIDDEN, "Công ty đang bị khoá, không thể chỉnh sửa hồ sơ.");
        }

        String oldTax = c.getTaxCode() == null ? "" : c.getTaxCode().trim();
        String newTax = request.taxCode() == null ? oldTax : request.taxCode().trim();
        boolean taxChanged = !newTax.isEmpty() && !newTax.equals(oldTax);

        c.setDisplayName(request.displayName().trim());
        c.setName(request.displayName().trim());
        if (!isBlank(request.taxCode())) c.setTaxCode(newTax);
        if (request.industry() != null) c.setIndustry(blankToNull(request.industry()));
        if (request.size() != null) c.setCompanySize(blankToNull(request.size()));
        if (request.companyType() != null) c.setCompanyType(blankToNull(request.companyType()));
        if (request.website() != null) c.setWebsite(blankToNull(request.website()));
        if (request.workingDays() != null) c.setWorkingDays(blankToNull(request.workingDays()));
        if (request.overtimePolicy() != null) c.setOvertimePolicy(blankToNull(request.overtimePolicy()));
        if (request.officeAddress() != null) {
            c.setOfficeAddress(blankToNull(request.officeAddress()));
            c.setAddress(blankToNull(request.officeAddress()));
        }
        if (request.description() != null) c.setDescription(blankToNull(request.description()));
        if (request.whyWorkHere() != null) c.setWhyWorkHere(blankToNull(request.whyWorkHere()));
        if (request.techStack() != null) {
            c.setTechStack(joinLines(request.techStack()));
        }
        if (!isBlank(request.logoFileName())) c.setLogoFileName(request.logoFileName().trim());
        if (!isBlank(request.coverFileName())) c.setCoverFileName(request.coverFileName().trim());

        if (taxChanged && c.getStatus() == CompanyStatus.ACTIVE) {
            c.setStatus(CompanyStatus.PENDING);
            c.setSubmittedAt(LocalDateTime.now());
            c.setRejectReason(null);
        }
        companyRepository.save(c);
        return toRecruiterProfileDto(c);
    }

    @Override
    @Transactional
    public RecruiterCompanyProfileDto uploadFile(String kind, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng chọn tệp hợp lệ.");
        }
        Company c = requireRecruiterCompany();
        String original = file.getOriginalFilename() != null ? file.getOriginalFilename() : "file";
        String normalizedKind = kind == null ? "license" : kind.trim().toLowerCase(Locale.ROOT);
        boolean image = "logo".equals(normalizedKind) || "cover".equals(normalizedKind);
        String contentType = file.getContentType() != null ? file.getContentType() : "application/octet-stream";
        if (image && (!IMAGE_TYPES.contains(contentType) || file.getSize() > MAX_IMAGE_BYTES)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Ảnh phải là PNG, JPEG hoặc WebP và không quá 5MB.");
        }

        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Không đọc được tệp tải lên.");
        }
        String key = ObjectKeys.companyFile(c.getId(), image ? normalizedKind : "license", original);
        String oldKey;
        switch (normalizedKind) {
            case "logo" -> {
                storageService.putPublic(key, bytes, contentType);
                oldKey = c.getLogoKey();
                c.setLogoFileName(original);
                c.setLogoKey(key);
            }
            case "cover" -> {
                storageService.putPublic(key, bytes, contentType);
                oldKey = c.getCoverKey();
                c.setCoverFileName(original);
                c.setCoverKey(key);
            }
            default -> {
                storageService.putPrivate(key, bytes, contentType);
                oldKey = c.getLicenseFileUrl();
                c.setLicenseFileName(original);
                c.setLicenseFileMeta(formatFileSize(file.getSize()));
                c.setLicenseFileUrl(key);
            }
        }
        companyRepository.save(c);
        // Chỉ xoá object cũ sau khi DB đã trỏ sang object mới.
        if (image) storageService.deletePublicQuietly(oldKey);
        else storageService.deletePrivateQuietly(oldKey);
        return toRecruiterProfileDto(c);
    }

    @Override
    @Transactional(readOnly = true)
    public List<CompanyDto> listAdmin(String status, String q, String city, String industry) {
        CompanyStatus parsed = parseStatusOrNull(status);
        return companyRepository.search(parsed, blankToNull(city), blankToNull(industry), blankToNull(q))
                .stream()
                .map(c -> toDto(c, null))
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public CompanyDto getAdmin(Integer id) {
        return toDto(requireCompany(id), null);
    }

    @Override
    @Transactional
    public CompanyDto approve(Integer id) {
        Company c = requireCompany(id);
        if (c.getStatus() != CompanyStatus.PENDING) {
            throw new ApiException(HttpStatus.CONFLICT, "Công ty này đã được xử lý trước đó. Vui lòng tải lại danh sách.");
        }
        c.setStatus(CompanyStatus.ACTIVE);
        c.setApprovedAt(LocalDateTime.now());
        c.setRejectReason(null);
        companyRepository.save(c);
        recordAdminAudit("APPROVE_COMPANY", "Duyệt công ty", "badge b-ok", c.getName());
        notifyCompanyReviewed(c, "Công ty đã được duyệt", c.getName(), "ACTIVE");
        return toDto(c, null);
    }

    @Override
    @Transactional
    public CompanyDto reject(Integer id, String reason) {
        String trimmed = reason == null ? "" : reason.trim();
        if (trimmed.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng nhập lý do từ chối.");
        }
        Company c = requireCompany(id);
        if (c.getStatus() != CompanyStatus.PENDING) {
            throw new ApiException(HttpStatus.CONFLICT, "Công ty này đã được xử lý trước đó. Vui lòng tải lại danh sách.");
        }
        c.setStatus(CompanyStatus.REJECTED);
        c.setRejectReason(trimmed);
        companyRepository.save(c);
        recordAdminAudit("REJECT_COMPANY", "Từ chối công ty", "badge b-warn", c.getName());
        notifyCompanyReviewed(c, "Hồ sơ công ty bị từ chối", c.getName() + " · " + trimmed, "REJECTED");
        return toDto(c, null);
    }

    private void notifyCompanyReviewed(Company c, String title, String body, String status) {
        List<Integer> recipientIds = recruiterProfileRepository.findByCompanyId(c.getId()).stream()
                .map(RecruiterProfile::getUserId)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        NotificationOutbox.publish(
                outboxWriter,
                NotificationConstants.RK_COMPANY_REVIEWED,
                NotificationType.COMPANY_STATUS,
                recipientIds,
                title,
                body,
                "/recruiter/company",
                Map.of("companyId", c.getId(), "status", status));
    }

    @Override
    @Transactional
    public CompanyDto lock(Integer id, String reason) {
        Company c = requireCompany(id);
        if (c.getStatus() != CompanyStatus.ACTIVE) {
            throw new ApiException(HttpStatus.CONFLICT, "Chỉ có thể khoá công ty đang hoạt động.");
        }
        c.setStatus(CompanyStatus.LOCKED);
        c.setRejectReason(isBlank(reason) ? "Bị khoá bởi quản trị viên." : reason.trim());
        companyRepository.save(c);
        recordAdminAudit("LOCK_COMPANY", "Khoá công ty", "badge b-danger", c.getName());
        return toDto(c, null);
    }

    @Override
    @Transactional
    public CompanyDto unlock(Integer id) {
        Company c = requireCompany(id);
        if (c.getStatus() != CompanyStatus.LOCKED) {
            throw new ApiException(HttpStatus.CONFLICT, "Công ty hiện không ở trạng thái bị khoá.");
        }
        c.setStatus(CompanyStatus.ACTIVE);
        c.setRejectReason(null);
        companyRepository.save(c);
        recordAdminAudit("UNLOCK_COMPANY", "Mở khoá công ty", "badge b-ok", c.getName());
        return toDto(c, null);
    }

    @Override
    @Transactional(readOnly = true)
    public FileLinkDto licenseLink(Integer id) {
        Company c = requireCompany(id);
        String key = c.getLicenseFileUrl();
        if (isBlank(key)) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Công ty chưa tải lên file giấy phép.");
        }
        if (!ObjectKeys.isObjectKey(key)) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Tệp giấy phép chưa được chuyển lên kho lưu trữ.");
        }
        return storageService.presignGet(key, firstNonBlank(c.getLicenseFileName(), "giay-phep.pdf"), true);
    }

    private void applyRegistrationFields(Company c, CompanyRegistrationRequest req) {
        String cleanName = req.name().trim();
        c.setLegalName(cleanName);
        if (isBlank(c.getDisplayName())) {
            c.setDisplayName(cleanName);
        }
        c.setName(c.getDisplayName());
        c.setTaxCode(blankToNull(req.taxCode()));
        c.setIndustry(blankToNull(req.industry()));
        c.setCompanySize(blankToNull(req.size()));
        c.setCompanyType(blankToNull(req.companyType()));
        c.setWebsite(blankToNull(req.website()));
        c.setFoundedYear(parseYearOrNull(req.foundedYear()));
        c.setHeadquarters(blankToNull(req.headquarters()));
        if (isBlank(c.getOfficeAddress())) {
            c.setOfficeAddress(blankToNull(req.headquarters()));
        }
        c.setAddress(blankToNull(req.headquarters()));
        c.setCity(deriveCity(req.headquarters()));
        c.setContactEmail(blankToNull(req.contactEmail()));
        c.setContactPhone(blankToNull(req.contactPhone()));
        c.setShortBio(blankToNull(req.shortBio()));
        c.setTagline(blankToNull(req.shortBio()));
        if (isBlank(c.getDescription())) {
            c.setDescription(blankToNull(req.shortBio()));
        }
        if (!isBlank(req.logoFileName())) c.setLogoFileName(req.logoFileName().trim());
        if (!isBlank(req.licenseFileName())) c.setLicenseFileName(req.licenseFileName().trim());
        if (!isBlank(req.licenseFileMeta())) c.setLicenseFileMeta(req.licenseFileMeta().trim());
        if (req.confirmed() != null) c.setConfirmed(req.confirmed());
    }

    private CompanyDto toDto(Company c, Integer currentUserId) {
        String name = firstNonBlank(c.getDisplayName(), c.getName());
        String legalName = firstNonBlank(c.getLegalName(), name);
        long openJobs = jobRepository.countByCompanyIdAndStatus(c.getId(), JobStatus.PUBLISHED);
        boolean following = currentUserId != null && followerRepository.existsByCompanyIdAndUserId(c.getId(), currentUserId);
        long followersCount = followerRepository.countByCompanyId(c.getId());

        return new CompanyDto(
                c.getId(),
                name,
                legalName,
                initials(name),
                firstNonBlank(c.getIndustry(), "Công nghệ thông tin"),
                firstNonBlank(c.getCompanySize(), "50–100 NV"),
                firstNonBlank(c.getCity(), deriveCity(firstNonBlank(c.getOfficeAddress(), c.getAddress()))),
                firstNonBlank(c.getTagline(), c.getShortBio()),
                firstNonBlank(c.getDescription(), c.getShortBio()),
                splitLines(firstNonBlank(c.getPerks(), c.getWhyWorkHere())),
                splitLines(c.getTechStack()),
                c.getFoundedYear(),
                c.getWebsite(),
                firstNonBlank(c.getWorkingDays(), "Thứ 2 – Thứ 6"),
                firstNonBlank(c.getOvertimePolicy(), "Không OT"),
                firstNonBlank(c.getOfficeAddress(), c.getAddress(), c.getHeadquarters()),
                firstNonBlank(c.getCompanyType(), "Product"),
                openJobs,
                c.getStatus(),
                c.getSubmittedAt() != null ? c.getSubmittedAt() : c.getCreatedAt(),
                firstNonBlank(c.getSubmittedByLabel(), "Nhà tuyển dụng"),
                c.getTaxCode(),
                c.getContactEmail(),
                c.getContactPhone(),
                c.getRejectReason(),
                new LicenseFileDto(
                        firstNonBlank(c.getLicenseFileName(), "GPKD.pdf"),
                        firstNonBlank(c.getLicenseFileMeta(), "Đã tải lên")
                ),
                following,
                followersCount,
                storageService.publicUrl(c.getLogoKey()),
                storageService.publicUrl(c.getCoverKey())
        );
    }

    private RecruiterCompanyProfileDto toRecruiterProfileDto(Company c) {
        String name = firstNonBlank(c.getLegalName(), c.getName());
        String display = firstNonBlank(c.getDisplayName(), c.getName());
        return new RecruiterCompanyProfileDto(
                c.getId(),
                name,
                display,
                orEmpty(c.getTaxCode()),
                firstNonBlank(c.getIndustry(), "Fintech"),
                firstNonBlank(c.getCompanySize(), "50 – 100"),
                firstNonBlank(c.getCompanyType(), "Product"),
                orEmpty(c.getWebsite()),
                c.getFoundedYear() != null ? String.valueOf(c.getFoundedYear()) : "",
                firstNonBlank(c.getHeadquarters(), c.getAddress(), ""),
                firstNonBlank(c.getOfficeAddress(), c.getAddress(), ""),
                orEmpty(c.getContactEmail()),
                orEmpty(c.getContactPhone()),
                firstNonBlank(c.getShortBio(), c.getTagline(), ""),
                orEmpty(c.getDescription()),
                orEmpty(c.getWhyWorkHere()),
                firstNonBlank(c.getWorkingDays(), "Thứ 2 – Thứ 6"),
                firstNonBlank(c.getOvertimePolicy(), "Không OT"),
                splitLines(c.getTechStack()),
                orEmpty(c.getLogoFileName()),
                orEmpty(c.getCoverFileName()),
                storageService.publicUrl(c.getLogoKey()),
                storageService.publicUrl(c.getCoverKey()),
                orEmpty(c.getLicenseFileName()),
                orEmpty(c.getLicenseFileMeta()),
                c.isConfirmed(),
                c.getStatus(),
                c.getSubmittedAt(),
                c.getApprovedAt(),
                firstNonBlank(c.getSubmittedByLabel(), ""),
                c.getRejectReason()
        );
    }

    private void recordAdminAudit(String eventType, String eventLabel, String badgeClass, String target) {
        try {
            UserPrincipal actor = SecurityUtils.currentUser();
            identityClient.recordAuditLog(eventType, eventLabel, badgeClass, target, actor.getId(), actor.getEmail());
        } catch (Exception ignored) {
        }
    }

    private Company requireCompany(Integer id) {
        return companyRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy thông tin công ty."));
    }

    private Company requireRecruiterCompany() {
        UserPrincipal principal = SecurityUtils.currentUser();
        RecruiterProfile profile = recruiterProfileRepository.findFirstByUserIdOrderByCreatedAtAsc(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Recruiter profile not found"));
        return profile.getCompany();
    }

    private Integer optionalUserId() {
        try {
            return SecurityUtils.currentUser().getId();
        } catch (Exception ex) {
            return null;
        }
    }

    private CompanyStatus parseStatusOrNull(String raw) {
        if (isBlank(raw) || "ALL".equalsIgnoreCase(raw.trim())) {
            return null;
        }
        try {
            return CompanyStatus.valueOf(raw.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Trạng thái công ty không hợp lệ.");
        }
    }

    private Integer parseYearOrNull(String raw) {
        if (isBlank(raw)) return null;
        try {
            return Integer.parseInt(raw.trim());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private String deriveCity(String address) {
        if (isBlank(address)) return "TP. Hồ Chí Minh";
        String low = address.toLowerCase(Locale.ROOT);
        if (low.contains("hà nội") || low.contains("ha noi")) return "Hà Nội";
        if (low.contains("đà nẵng") || low.contains("da nang")) return "Đà Nẵng";
        if (low.contains("remote")) return "Remote";
        if (low.contains("hồ chí minh") || low.contains("hcm") || low.contains("tp.hcm")) return "TP. Hồ Chí Minh";
        return address.trim();
    }

    private String initials(String name) {
        if (isBlank(name)) return "CT";
        String[] parts = name.trim().split("\\s+");
        if (parts.length == 1) {
            return parts[0].substring(0, Math.min(2, parts[0].length())).toUpperCase(Locale.ROOT);
        }
        return (parts[0].substring(0, 1) + parts[parts.length - 1].substring(0, 1)).toUpperCase(Locale.ROOT);
    }

    private List<String> splitLines(String text) {
        if (isBlank(text)) return List.of();
        return Arrays.stream(text.split("[\\r\\n,]+"))
                .map(String::trim)
                .map(s -> s.startsWith("- ") ? s.substring(2).trim() : s)
                .filter(s -> !s.isEmpty())
                .toList();
    }

    private String joinLines(List<String> items) {
        if (items == null || items.isEmpty()) return null;
        return items.stream().filter(s -> !isBlank(s)).map(String::trim).reduce((a, b) -> a + "\n" + b).orElse(null);
    }

    private String formatActorLabel(UserPrincipal principal) {
        if (isBlank(principal.getFullName())) return principal.getEmail();
        return principal.getFullName() + " (" + principal.getEmail() + ")";
    }

    private String formatFileSize(long bytes) {
        if (bytes >= 1024 * 1024) {
            return String.format(Locale.US, "%.1f MB", bytes / (1024.0 * 1024.0)).replace('.', ',');
        }
        return Math.max(1, Math.round(bytes / 1024.0)) + " KB";
    }

    private boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    private String blankToNull(String s) {
        return isBlank(s) ? null : s.trim();
    }

    private String orEmpty(String s) {
        return s == null ? "" : s;
    }

    private String firstNonBlank(String... values) {
        for (String v : values) {
            if (!isBlank(v)) return v.trim();
        }
        return null;
    }
}
