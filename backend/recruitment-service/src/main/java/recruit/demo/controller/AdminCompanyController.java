package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.CompanyDtos.*;
import recruit.demo.service.CompanyService;

import java.util.List;

@RestController
@RequestMapping("/api/admin/companies")
@RequiredArgsConstructor
@PreAuthorize("hasRole('ADMIN') or hasAuthority('company:approve')")
public class AdminCompanyController {

    private final CompanyService companyService;

    @GetMapping
    public BaseResponse<List<CompanyDto>> list(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) String industry
    ) {
        return BaseResponse.success(companyService.listAdmin(status, q, city, industry));
    }

    @GetMapping("/{id}")
    public BaseResponse<CompanyDto> get(@PathVariable Integer id) {
        return BaseResponse.success(companyService.getAdmin(id));
    }

    @PostMapping("/{id}/approve")
    public BaseResponse<CompanyDto> approve(@PathVariable Integer id) {
        return BaseResponse.success(companyService.approve(id));
    }

    @PostMapping("/{id}/reject")
    public BaseResponse<CompanyDto> reject(@PathVariable Integer id, @Valid @RequestBody RejectCompanyRequest request) {
        return BaseResponse.success(companyService.reject(id, request.reason()));
    }

    @PostMapping("/{id}/lock")
    public BaseResponse<CompanyDto> lock(@PathVariable Integer id, @RequestBody(required = false) LockCompanyRequest request) {
        return BaseResponse.success(companyService.lock(id, request != null ? request.reason() : null));
    }

    @PostMapping("/{id}/unlock")
    public BaseResponse<CompanyDto> unlock(@PathVariable Integer id) {
        return BaseResponse.success(companyService.unlock(id));
    }

    @GetMapping("/{id}/license")
    public ResponseEntity<Resource> downloadLicense(@PathVariable Integer id) {
        Resource resource = companyService.loadLicenseFile(id);
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_PDF)
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + resource.getFilename() + "\"")
                .body(resource);
    }
}
