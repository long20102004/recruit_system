package recruit.demo.cvtemplate;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.storage.StorageService;

import java.util.List;

/** Danh sách mẫu CV đang hoạt động cho ứng viên (C02, C04). */
@RestController
@RequestMapping("/api/cv-templates")
@RequiredArgsConstructor
@PreAuthorize("hasAuthority('cv:manage-own')")
public class CandidateCvTemplateController {

    private final CvTemplateRepository cvTemplateRepository;
    private final StorageService storageService;

    @GetMapping
    public BaseResponse<List<CandidateCvTemplateDto>> list() {
        List<CandidateCvTemplateDto> items = cvTemplateRepository
                .findByStatusOrderByDefaultTemplateDescIdAsc(CvTemplateStatus.ACTIVE)
                .stream()
                .map(this::toDto)
                .toList();
        return BaseResponse.success(items);
    }

    private CandidateCvTemplateDto toDto(CvTemplate template) {
        String thumbnailUrl = null;
        if (template.getThumbnailKey() != null && !template.getThumbnailKey().isBlank()) {
            FileLinkDto link = storageService.presignGet(template.getThumbnailKey(), "thumb.png", true);
            thumbnailUrl = link != null ? link.getUrl() : null;
        }
        return CandidateCvTemplateDto.builder()
                .id(template.getId())
                .name(template.getName())
                .type(template.getType())
                .defaultTemplate(template.isDefaultTemplate())
                .thumbnailUrl(thumbnailUrl)
                .config(template.getConfig())
                .build();
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CandidateCvTemplateDto {
        private Integer id;
        private String name;
        private CvTemplateType type;

        @JsonProperty("isDefault")
        private boolean defaultTemplate;

        private String thumbnailUrl;
        private CvTemplateConfig config;
    }
}
