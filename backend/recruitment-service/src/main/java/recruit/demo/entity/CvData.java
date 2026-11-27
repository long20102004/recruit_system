package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "cv_data")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CvData {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "candidate_id", nullable = false)
    private Integer candidateId;

    @Column(name = "cv_id", nullable = false)
    private Integer cvId;

    @Column(nullable = false)
    private String field;

    @Column(columnDefinition = "TEXT")
    private String value;
}
