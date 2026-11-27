package recruit.demo.dto;

import jakarta.validation.constraints.NotBlank;
import recruit.demo.enums.CompanyStatus;

import java.time.LocalDateTime;
import java.util.List;

public final class CompanyDtos {

    private CompanyDtos() {
    }

    public record LicenseFileDto(String name, String meta) {
    }

    public record CompanyDto(
            Integer id,
            String name,
            String legalName,
            String logo,
            String industry,
            String size,
            String city,
            String tagline,
            String about,
            List<String> perks,
            List<String> skills,
            Integer founded,
            String website,
            String workingDays,
            String overtime,
            String address,
            String workMode,
            long openJobsCount,
            CompanyStatus status,
            LocalDateTime submittedAt,
            String submittedBy,
            String taxCode,
            String email,
            String phone,
            String rejectReason,
            LicenseFileDto licenseFile,
            boolean following,
            long followersCount,
            /** URL công khai trên R2; null khi chưa tải ảnh. */
            String logoUrl,
            String coverUrl
    ) {
    }

    public record RecruiterCompanyProfileDto(
            Integer id,
            String name,
            String displayName,
            String taxCode,
            String industry,
            String size,
            String companyType,
            String website,
            String foundedYear,
            String headquarters,
            String officeAddress,
            String contactEmail,
            String contactPhone,
            String shortBio,
            String description,
            String whyWorkHere,
            String workingDays,
            String overtimePolicy,
            List<String> techStack,
            String logoFileName,
            String coverFileName,
            /** URL công khai trên R2; null khi chưa tải ảnh. */
            String logoUrl,
            String coverUrl,
            String licenseFileName,
            String licenseFileMeta,
            boolean confirmed,
            CompanyStatus status,
            LocalDateTime submittedAt,
            LocalDateTime approvedAt,
            String createdBy,
            String rejectionReason
    ) {
    }

    public record CompanyRegistrationRequest(
            String name,
            String taxCode,
            String industry,
            String size,
            String companyType,
            String website,
            String foundedYear,
            String headquarters,
            String contactEmail,
            String contactPhone,
            String shortBio,
            String logoFileName,
            String licenseFileName,
            String licenseFileMeta,
            Boolean confirmed
    ) {
    }

    public record CompanyProfileUpdateRequest(
            @NotBlank String displayName,
            String taxCode,
            String industry,
            String size,
            String companyType,
            String website,
            String workingDays,
            String overtimePolicy,
            String officeAddress,
            String description,
            String whyWorkHere,
            List<String> techStack,
            String logoFileName,
            String coverFileName
    ) {
    }

    public record RejectCompanyRequest(@NotBlank String reason) {
    }

    public record LockCompanyRequest(String reason) {
    }

    public record FollowResponse(Integer companyId, boolean following, long followersCount) {
    }
}
