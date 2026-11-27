package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;
import recruit.demo.enums.CompanyStatus;

import java.time.LocalDateTime;

@Entity
@Table(name = "companies")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Company {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(nullable = false)
    private String name;

    @Column(name = "legal_name")
    private String legalName;

    @Column(name = "display_name")
    private String displayName;

    @Column(name = "tax_code", length = 64)
    private String taxCode;

    @Column(length = 120)
    private String industry;

    @Column(name = "company_size", length = 80)
    private String companySize;

    @Column(name = "company_type", length = 80)
    private String companyType;

    @Column(name = "founded_year")
    private Integer foundedYear;

    @Column(length = 120)
    private String city;

    @Column(length = 500)
    private String headquarters;

    @Column(name = "office_address", length = 500)
    private String officeAddress;

    @Column(name = "contact_email")
    private String contactEmail;

    @Column(name = "contact_phone", length = 64)
    private String contactPhone;

    @Column(length = 500)
    private String tagline;

    @Column(name = "short_bio", columnDefinition = "TEXT")
    private String shortBio;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "why_work_here", columnDefinition = "TEXT")
    private String whyWorkHere;

    @Column(name = "working_days", length = 120)
    private String workingDays;

    @Column(name = "overtime_policy", length = 120)
    private String overtimePolicy;

    @Column(name = "tech_stack", columnDefinition = "TEXT")
    private String techStack;

    @Column(columnDefinition = "TEXT")
    private String perks;

    private String website;
    private String address;

    @Column(name = "logo_file_name")
    private String logoFileName;

    @Column(name = "cover_file_name")
    private String coverFileName;

    @Column(name = "license_file_name")
    private String licenseFileName;

    @Column(name = "license_file_meta", length = 120)
    private String licenseFileMeta;

    /** Object key trên R2 (bucket private); bản ghi cũ có thể còn là đường dẫn local chờ migrate. */
    @Column(name = "license_file_url", length = 500)
    private String licenseFileUrl;

    /** Object key logo trên bucket public R2 (specs/008-r2-storage). */
    @Column(name = "logo_key", length = 512)
    private String logoKey;

    /** Object key ảnh bìa trên bucket public R2. */
    @Column(name = "cover_key", length = 512)
    private String coverKey;

    @Column(nullable = false)
    @Builder.Default
    private boolean confirmed = false;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    @Builder.Default
    private CompanyStatus status = CompanyStatus.ACTIVE;

    @Column(name = "reject_reason", columnDefinition = "TEXT")
    private String rejectReason;

    @Column(name = "submitted_at")
    private LocalDateTime submittedAt;

    @Column(name = "approved_at")
    private LocalDateTime approvedAt;

    @Column(name = "submitted_by_user_id")
    private Integer submittedByUserId;

    @Column(name = "submitted_by_label")
    private String submittedByLabel;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
