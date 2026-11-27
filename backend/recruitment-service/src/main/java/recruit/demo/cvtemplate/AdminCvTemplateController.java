package recruit.demo.cvtemplate;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.cvtemplate.CvTemplateDtos.AdminCvTemplateDto;
import recruit.demo.cvtemplate.CvTemplateDtos.CreateConfigTemplateRequest;
import recruit.demo.cvtemplate.CvTemplateDtos.UpdateConfigTemplateRequest;
import recruit.demo.cvtemplate.CvTemplateDtos.UpdateTemplateStatusRequest;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.FileLinkDto;

import java.nio.charset.StandardCharsets;
import java.util.List;

/** API Admin quản lý mẫu CV (CONFIG & DOCX). */
@RestController
@RequestMapping("/api/admin/cv-templates")
@RequiredArgsConstructor
@PreAuthorize("hasAuthority('cv-template:manage')")
public class AdminCvTemplateController {

    private static final String PREVIEW_CSP = "default-src 'none'; style-src 'unsafe-inline'; font-src data:";
    private static final MediaType DOCX_MEDIA_TYPE = MediaType.parseMediaType(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    private static final MediaType HTML_UTF8_MEDIA_TYPE = new MediaType(MediaType.TEXT_HTML, StandardCharsets.UTF_8);

    private final AdminCvTemplateService adminCvTemplateService;

    @GetMapping
    public BaseResponse<List<AdminCvTemplateDto>> list() {
        return BaseResponse.success(adminCvTemplateService.listAll());
    }

    @GetMapping("/options")
    public BaseResponse<CvTemplateOptions.OptionsResponse> options() {
        return BaseResponse.success(adminCvTemplateService.options());
    }

    @GetMapping("/docx-sample")
    public ResponseEntity<byte[]> downloadDocxSample() {
        byte[] bytes = adminCvTemplateService.loadDocxSample();
        return ResponseEntity.ok()
                .contentType(DOCX_MEDIA_TYPE)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment().filename("harvard-cv-template.docx").build().toString())
                .body(bytes);
    }

    @PostMapping
    public BaseResponse<AdminCvTemplateDto> createConfig(@Valid @RequestBody CreateConfigTemplateRequest request) {
        return BaseResponse.success(adminCvTemplateService.createConfig(request));
    }

    @PostMapping(value = "/docx", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BaseResponse<AdminCvTemplateDto> createDocx(
            @RequestPart("file") MultipartFile file,
            @RequestParam("name") String name
    ) {
        return BaseResponse.success(adminCvTemplateService.createDocx(file, name));
    }

    @PutMapping("/{id}")
    public BaseResponse<AdminCvTemplateDto> updateConfig(
            @PathVariable Integer id,
            @Valid @RequestBody UpdateConfigTemplateRequest request
    ) {
        return BaseResponse.success(adminCvTemplateService.updateConfig(id, request));
    }

    @PutMapping(value = "/{id}/docx", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BaseResponse<AdminCvTemplateDto> replaceDocx(
            @PathVariable Integer id,
            @RequestPart("file") MultipartFile file
    ) {
        return BaseResponse.success(adminCvTemplateService.replaceDocx(id, file));
    }

    @PatchMapping("/{id}/status")
    public BaseResponse<AdminCvTemplateDto> updateStatus(
            @PathVariable Integer id,
            @Valid @RequestBody UpdateTemplateStatusRequest request
    ) {
        return BaseResponse.success(adminCvTemplateService.updateStatus(id, request.getStatus()));
    }

    @PostMapping("/{id}/default")
    public BaseResponse<AdminCvTemplateDto> setDefault(@PathVariable Integer id) {
        return BaseResponse.success(adminCvTemplateService.setDefault(id));
    }

    @DeleteMapping("/{id}")
    public BaseResponse<Void> delete(@PathVariable Integer id) {
        adminCvTemplateService.delete(id);
        return BaseResponse.success(null);
    }

    @PostMapping("/preview")
    public ResponseEntity<String> previewHtml(@RequestBody CvTemplateConfig config) {
        String html = adminCvTemplateService.previewConfigHtml(config);
        return ResponseEntity.ok()
                .contentType(HTML_UTF8_MEDIA_TYPE)
                .header("Content-Security-Policy", PREVIEW_CSP)
                .body(html);
    }

    @GetMapping("/{id}/preview-pdf")
    public BaseResponse<FileLinkDto> previewPdf(@PathVariable Integer id) {
        return BaseResponse.success(adminCvTemplateService.previewPdf(id));
    }
}
