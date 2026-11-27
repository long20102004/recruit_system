package recruit.demo.controller;

import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.CandidateProfileDto;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.dto.CvDocumentDtos.CvDocumentDto;
import recruit.demo.dto.CvDocumentDtos.CvUploadResponse;
import recruit.demo.dto.CvDocumentDtos.RenameCvRequest;
import recruit.demo.dto.CvFormResponse;
import recruit.demo.service.CvService;

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

    /** API cũ: trích xuất CV PDF vào CV chính; data là profile AI đọc được (cùng DTO với /analyze-pdf). */
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
    public List<CvDocumentDto> documents() {
        return cvService.documents();
    }

    /** Thêm một CV mới (tối đa 5). */
    @PostMapping(value = "/documents", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BaseResponse<CvUploadResponse> uploadNew(@RequestPart("file") MultipartFile file,
                                                    @RequestParam(required = false) String title) {
        return BaseResponse.success(cvService.uploadNew(file, title));
    }

    /** Tải lại file PDF cho một CV đã có. */
    @PostMapping(value = "/documents/{id}/file", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BaseResponse<CvUploadResponse> reupload(@PathVariable Integer id,
                                                   @RequestPart("file") MultipartFile file) {
        return BaseResponse.success(cvService.reupload(id, file));
    }

    @PatchMapping("/documents/{id}")
    public CvDocumentDto rename(@PathVariable Integer id, @RequestBody RenameCvRequest request) {
        return cvService.rename(id, request == null ? null : request.title());
    }

    @PostMapping("/documents/{id}/main")
    public List<CvDocumentDto> setMain(@PathVariable Integer id) {
        return cvService.setMain(id);
    }

    @DeleteMapping("/documents/{id}")
    public ResponseEntity<Void> delete(@PathVariable Integer id) {
        cvService.delete(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/documents/{id}/file")
    public ResponseEntity<Resource> file(@PathVariable Integer id) {
        Resource file = cvService.file(id);
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + file.getFilename() + "\"")
                .body(file);
    }
}
