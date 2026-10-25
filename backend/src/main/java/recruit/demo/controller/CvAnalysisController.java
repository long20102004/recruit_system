package recruit.demo.controller;

import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.service.RuleBasedCvExtractionService;
import recruit.demo.service.CvAnalysisService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/cv")
@RequiredArgsConstructor
public class CvAnalysisController {

    private final CvAnalysisService cvAnalysisService;
    private final RuleBasedCvExtractionService ruleBasedService;

    @PostMapping("/analyze")
    public ResponseEntity<CandidateProfile> analyzeCv(@RequestBody String rawCvText) {
        CandidateProfile profile = cvAnalysisService.analyzeCv(rawCvText);
        return ResponseEntity.ok(profile);
    }

    @PostMapping(value = "/analyze-pdf", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<CandidateProfile> analyzeCvPdf(@RequestParam("file") MultipartFile file) {
        CandidateProfile profile = cvAnalysisService.analyzeCvPdf(file);
        return ResponseEntity.ok(profile);
    }

    @PostMapping(value = "/extract-text", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Map<String, Object>> extractPdfText(@RequestParam("file") MultipartFile file) {
        String text = cvAnalysisService.extractPdfText(file);
        String fileName = file.getOriginalFilename() == null ? "" : file.getOriginalFilename();
        return ResponseEntity.ok(Map.of(
                "filename", fileName,
                "chars", text.length(),
                "text", text
        ));
    }

    /**
     * Pipeline rule-based cục bộ (không gọi LLM): PDF → PDFBox tọa độ →
     * layout → section → regex/từ điển → state machine → JSON schema.
     */
    @PostMapping(value = "/extract-rule-based", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<CandidateProfile> extractRuleBased(@RequestParam("file") MultipartFile file) {
        CandidateProfile profile = ruleBasedService.extractPdf(file);
        return ResponseEntity.ok(profile);
    }
}
