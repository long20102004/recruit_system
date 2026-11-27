package recruit.demo.cvtemplate;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;

@Entity
@Table(name = "cv_templates")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CvTemplate {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(nullable = false, length = 80, unique = true)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private CvTemplateType type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    @Builder.Default
    private CvTemplateStatus status = CvTemplateStatus.ACTIVE;

    @Column(name = "is_default", nullable = false)
    private boolean defaultTemplate;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "json")
    private CvTemplateConfig config;

    @Column(name = "docx_key", length = 512)
    private String docxKey;

    @Column(name = "preview_pdf_key", length = 512)
    private String previewPdfKey;

    @Column(name = "thumbnail_key", length = 512)
    private String thumbnailKey;

    @Column(name = "created_by")
    private Integer createdBy;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
