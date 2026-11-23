package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.dto.CvDtos;
import recruit.demo.service.CvService;

@RestController
@RequestMapping("/api/cvs")
@RequiredArgsConstructor
public class CvController {

    private final CvService cvService;

    @GetMapping
    public CvDtos.CvFormResponse mine() {
        return cvService.mine();
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public CvDtos.CvFormResponse upload(@RequestPart("file") MultipartFile file) {
        return cvService.upload(file);
    }

    @PutMapping
    public CvDtos.CvFormResponse confirm(@RequestBody CvDtos.ConfirmCvRequest request) {
        return cvService.confirm(request);
    }
}
