package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.CompanyDtos.*;
import recruit.demo.service.CompanyService;

@RestController
@RequestMapping("/api/recruiter/company")
@RequiredArgsConstructor
@PreAuthorize("hasRole('RECRUITER') or hasAuthority('company:manage')")
public class RecruiterCompanyController {

    private final CompanyService companyService;

    @GetMapping
    public BaseResponse<RecruiterCompanyProfileDto> myCompany() {
        return BaseResponse.success(companyService.getMyCompany());
    }

    @PutMapping("/draft")
    public BaseResponse<RecruiterCompanyProfileDto> saveDraft(@RequestBody CompanyRegistrationRequest request) {
        return BaseResponse.success(companyService.saveDraft(request));
    }

    @PostMapping("/submit")
    public BaseResponse<RecruiterCompanyProfileDto> submit(@RequestBody CompanyRegistrationRequest request) {
        return BaseResponse.success(companyService.submitRegistration(request));
    }

    @PutMapping
    public BaseResponse<RecruiterCompanyProfileDto> updateProfile(@Valid @RequestBody CompanyProfileUpdateRequest request) {
        return BaseResponse.success(companyService.updateProfile(request));
    }

    @PostMapping("/files")
    public BaseResponse<RecruiterCompanyProfileDto> uploadFile(
            @RequestParam(defaultValue = "license") String kind,
            @RequestParam("file") MultipartFile file
    ) {
        return BaseResponse.success(companyService.uploadFile(kind, file));
    }
}
