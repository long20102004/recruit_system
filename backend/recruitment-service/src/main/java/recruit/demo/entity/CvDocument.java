package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/** Một CV của ứng viên. Nội dung nằm trong {@link CvData} theo cv_id; mỗi ứng viên có đúng 1 CV chính. */
@Entity
@Table(name = "cv_documents")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CvDocument {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "candidate_id", nullable = false)
    private Integer candidateId;

    private String title;

    @Column(name = "is_main", nullable = false)
    private boolean main;

    @Column(name = "template_id")
    private Integer templateId;

    @Column(name = "generated_pdf_key", length = 512)
    private String generatedPdfKey;

    @Column(name = "generated_at")
    private LocalDateTime generatedAt;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
