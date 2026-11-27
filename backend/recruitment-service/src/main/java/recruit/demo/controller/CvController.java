package recruit.demo.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.CandidateProfileDto;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.dto.CvDocumentDtos.CreateCvRequest;
import recruit.demo.dto.CvDocumentDtos.CvDocumentDto;
import recruit.demo.dto.CvDocumentDtos.CvUploadResponse;
import recruit.demo.dto.CvDocumentDtos.RenameCvRequest;
import recruit.demo.dto.CvFormResponse;
import recruit.demo.dto.CvTemplateSelectionDtos.CvPreviewRequest;
import recruit.demo.dto.CvTemplateSelectionDtos.CvPreviewResult;
import recruit.demo.dto.CvTemplateSelectionDtos.SetTemplateRequest;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.service.CvService;

import java.nio.charset.StandardCharsets;
import java.util.List;

/** CV của ứng viên. Không truyền cvId thì làm trên CV chính (tương thích API một CV cũ). */
@RestController
@RequestMapping("/api/cvs")
@RequiredArgsConstructor
@PreAuthorize("hasAuthority('cv:manage-own')")
public class CvController {

    private final CvService cvService;

    @GetMapping
    public CvFormResponse mine(@RequestParam(required = false) Integer cvId) {
        return cvService.mine(cvId);
    }

    /** API cũ: trích xuất CV PDF/DOCX vào CV chính; data là profile AI đọc được (cùng DTO với /analyze-pdf). */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BaseResponse<CandidateProfileDto> upload(@RequestPart("file") MultipartFile file) {
        return BaseResponse.success(cvService.upload(file));
    }

    @PutMapping
    public CvFormResponse confirm(@RequestParam(required = false) Integer cvId,
                                  @RequestBody ConfirmCvRequest request) {
        return cvService.confirm(cvId, request);
    }

    @GetMapping("/documents")
    public BaseResponse<List<CvDocumentDto>> documents() {
        return BaseResponse.success(cvService.documents());
    }

    /** Thêm một CV mới (tối đa 5). */
    @PostMapping(value = "/documents", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BaseResponse<CvUploadResponse> uploadNew(@RequestPart("file") MultipartFile file,
                                                    @RequestParam(required = false) String title) {
        return BaseResponse.success(cvService.uploadNew(file, title));
    }

    /** Tải lại file PDF/DOCX cho một CV đã có. */
    @PostMapping(value = "/documents/{id}/file", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BaseResponse<CvUploadResponse> reupload(@PathVariable Integer id,
                                                   @RequestPart("file") MultipartFile file) {
        return BaseResponse.success(cvService.reupload(id, file));
    }

    /** Tạo CV từ đầu (C04): CV trống, chưa có file; đủ 5 CV trả 400. */
    @PostMapping("/documents/blank")
    public BaseResponse<CvDocumentDto> createBlank(@RequestBody(required = false) CreateCvRequest request) {
        return BaseResponse.success(cvService.createBlank(
                request == null ? null : request.getTitle(),
                request == null ? null : request.getTemplateId()));
    }

    /** Gắn / đổi mẫu CV cho CV form (C04). */
    @PutMapping("/documents/{id}/template")
    public BaseResponse<CvDocumentDto> setTemplate(@PathVariable Integer id,
                                                   @RequestBody(required = false) SetTemplateRequest request) {
        return BaseResponse.success(cvService.setTemplate(id, request == null ? null : request.getTemplateId()));
    }

    /** Xem trước CV chưa lưu: mẫu CONFIG trả text/html (CSP); mẫu DOCX trả FileLinkDto PDF. */
    @PostMapping("/preview")
    public ResponseEntity<?> preview(@RequestBody(required = false) CvPreviewRequest request) {
        CvPreviewResult result = cvService.preview(request);
        if (result.getHtml() != null) {
            return ResponseEntity.ok()
                    .contentType(new MediaType(MediaType.TEXT_HTML, StandardCharsets.UTF_8))
                    .header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; font-src data:")
                    .body(result.getHtml());
        }
        return ResponseEntity.ok(BaseResponse.success(result.getPdfLink()));
    }

    /** Sinh PDF từ dữ liệu đã lưu theo mẫu đang chọn và lưu R2. */
    @PostMapping("/documents/{id}/pdf")
    public BaseResponse<FileLinkDto> generatePdf(@PathVariable Integer id) {
        return BaseResponse.success(cvService.generatePdf(id));
    }

    @PatchMapping("/documents/{id}")
    public BaseResponse<CvDocumentDto> rename(@PathVariable Integer id, @RequestBody RenameCvRequest request) {
        return BaseResponse.success(cvService.rename(id, request == null ? null : request.getTitle()));
    }

    @PostMapping("/documents/{id}/main")
    public BaseResponse<List<CvDocumentDto>> setMain(@PathVariable Integer id) {
        return BaseResponse.success(cvService.setMain(id));
    }

    @DeleteMapping("/documents/{id}")
    public ResponseEntity<Void> delete(@PathVariable Integer id) {
        cvService.delete(id);
        return ResponseEntity.noContent().build();
    }

    /** Link ký tạm để tải file PDF/DOCX gốc từ R2 (specs/008-r2-storage). */
    @GetMapping("/documents/{id}/file")
    public BaseResponse<FileLinkDto> file(@PathVariable Integer id) {
        return BaseResponse.success(cvService.file(id));
    }
}
