package recruit.demo.controller;

import recruit.demo.dto.FileLinkDto;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ApplicationDtos.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.ApplicationService;

import java.util.List;

@RestController
@RequestMapping("/api/applications")
@RequiredArgsConstructor
public class ApplicationsController {

    private final ApplicationService applicationService;

    @PostMapping("/jobs/{jobId}")
    @PreAuthorize("hasAuthority('application:apply')")
    public ApplicationResponse apply(@PathVariable Integer jobId,
                                     @RequestBody(required = false) ApplyRequest request) {
        return applicationService.apply(jobId, request);
    }

    @GetMapping("/mine")
    @PreAuthorize("hasAuthority('application:read-own')")
    public BaseResponse<PageResponse<ApplicationResponse>> myApplications(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(applicationService.myApplications(Paging.of(page, size)));
    }

    @GetMapping("/recruiter")
    @PreAuthorize("hasAuthority('application:read-received')")
    public BaseResponse<PageResponse<ApplicationResponse>> recruiterApplications(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Integer jobId,
            @RequestParam(required = false) Integer minMatchScore,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(applicationService.recruiterApplications(status, jobId, minMatchScore, Paging.of(page, size)));
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasAuthority('application:read-received') or hasAuthority('application:read-own')")
    public BaseResponse<ApplicationDetailResponse> detail(@PathVariable Integer id) {
        return BaseResponse.success(applicationService.getDetail(id));
    }

    @PatchMapping("/{id}/status")
    @PreAuthorize("hasAuthority('application:read-received') or hasAuthority('application:update-status')")
    public BaseResponse<ApplicationDetailResponse> updateStatus(@PathVariable Integer id,
                                                                @Valid @RequestBody UpdateApplicationStatusRequest request) {
        return BaseResponse.success(applicationService.updateStatus(id, request.status(), request.note()));
    }

    @PatchMapping("/bulk-status")
    @PreAuthorize("hasAuthority('application:read-received') or hasAuthority('application:update-status')")
    public BaseResponse<List<ApplicationResponse>> bulkUpdateStatus(@Valid @RequestBody BulkUpdateStatusRequest request) {
        return BaseResponse.success(applicationService.bulkUpdateStatus(request.applicationIds(), request.status(), request.note()));
    }

    @PostMapping("/{id}/withdraw")
    @PreAuthorize("hasAuthority('application:read-own')")
    public BaseResponse<ApplicationDetailResponse> withdraw(@PathVariable Integer id) {
        return BaseResponse.success(applicationService.withdraw(id));
    }

    @PutMapping("/{id}/note")
    @PreAuthorize("hasAuthority('application:read-received')")
    public BaseResponse<ApplicationDetailResponse> saveNote(@PathVariable Integer id,
                                                            @Valid @RequestBody UpdateApplicationNoteRequest request) {
        return BaseResponse.success(applicationService.saveNote(id, request.rating(), request.internalNote()));
    }

    @GetMapping("/{id}/history")
    @PreAuthorize("hasAuthority('application:read-received') or hasAuthority('application:read-own')")
    public BaseResponse<List<ApplicationHistoryDto>> history(@PathVariable Integer id) {
        return BaseResponse.success(applicationService.history(id));
    }

    @GetMapping("/{id}/cv-file")
    @PreAuthorize("hasAuthority('application:read-received') or hasAuthority('application:read-own')")
    public BaseResponse<FileLinkDto> downloadCvFile(@PathVariable Integer id) {
        return BaseResponse.success(applicationService.loadCvFile(id));
    }
}
