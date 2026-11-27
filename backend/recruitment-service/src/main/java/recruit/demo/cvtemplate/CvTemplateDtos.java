package recruit.demo.cvtemplate;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/** DTOs cho API quản trị mẫu CV (/api/admin/cv-templates). */
public final class CvTemplateDtos {

    private CvTemplateDtos() {
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AdminCvTemplateDto {
        private Integer id;
        private String name;
        private CvTemplateType type;
        private CvTemplateStatus status;
        @JsonProperty("isDefault")
        private boolean defaultTemplate;
        private CvTemplateConfig config;
        private long usedCount;
        private String thumbnailUrl;
        private boolean hasPreviewPdf;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CreateConfigTemplateRequest {
        @NotBlank(message = "Tên mẫu không được để trống")
        @Size(max = 80, message = "Tên mẫu tối đa 80 ký tự")
        private String name;

        @NotNull(message = "Cấu hình mẫu không được để trống")
        private CvTemplateConfig config;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpdateConfigTemplateRequest {
        @NotBlank(message = "Tên mẫu không được để trống")
        @Size(max = 80, message = "Tên mẫu tối đa 80 ký tự")
        private String name;

        @NotNull(message = "Cấu hình mẫu không được để trống")
        private CvTemplateConfig config;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UpdateTemplateStatusRequest {
        @NotNull(message = "Trạng thái không được để trống")
        private CvTemplateStatus status;
    }
}
