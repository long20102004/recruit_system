package recruit.demo.entity;

import jakarta.persistence.*;
import lombok.*;

/** Một quyền nghiệp vụ dạng "resource:action" (bảng permissions, specs/004-rbac). */
@Entity
@Table(name = "permissions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class AppPermission {
    @Id
    @Column(length = 64)
    private String code;

    @Column(nullable = false, length = 32)
    private String resource;

    @Column(nullable = false)
    private String description;
}
