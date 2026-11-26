package recruit.demo.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.CandidateProfileDto;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.dto.CvFormResponse;
import recruit.demo.service.CvService;

@RestController
@RequestMapping("/api/cvs")
@RequiredArgsConstructor
public class CvController {

    private final CvService cvService;

    @GetMapping

    @PreAuthorize("hasAuthority('cv:manage-own')")
    public CvFormResponse mine() {
        return cvService.mine();
    }

    /** Trích xuất CV PDF; data là profile AI đọc được (cùng DTO với /analyze-pdf). */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @PreAuthorize("hasAuthority('cv:manage-own')")
    public BaseResponse<CandidateProfileDto> upload(@RequestPart("file") MultipartFile file) {
        return BaseResponse.success(cvService.upload(file));
    }

    @PutMapping

    @PreAuthorize("hasAuthority('cv:manage-own')")
    public CvFormResponse confirm(@RequestBody ConfirmCvRequest request) {
        return cvService.confirm(request);
    }
}
