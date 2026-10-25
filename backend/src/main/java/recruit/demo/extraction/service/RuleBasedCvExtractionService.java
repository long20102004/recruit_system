package recruit.demo.extraction.service;

import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.mapping.CvJsonMapper;
import recruit.demo.extraction.pdf.PdfTextExtractor;
import recruit.demo.extraction.pdf.TextBlock;
import recruit.demo.extraction.section.CvSection;
import recruit.demo.extraction.section.SectionContent;
import recruit.demo.extraction.section.SectionDetector;
import recruit.demo.extraction.validation.CvValidator;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * Điều phối pipeline rule-based: PDF → blocks → sections → fields → JSON → validate.
 * Chạy HOÀN TOÀN cục bộ bằng Java, không gọi LLM (bổ sung bên cạnh luồng LLM hiện có).
 */
@Service
@Slf4j
public class RuleBasedCvExtractionService {

    private final PdfTextExtractor pdfTextExtractor = new PdfTextExtractor();
    private final SectionDetector sectionDetector = new SectionDetector();
    private final CvJsonMapper mapper = new CvJsonMapper();
    private final CvValidator validator = new CvValidator();

    public CandidateProfile extractPdf(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("File PDF không được để trống");
        }
        String fileName = file.getOriginalFilename();
        if (fileName != null && !fileName.toLowerCase().endsWith(".pdf")) {
            throw new IllegalArgumentException("Định dạng file không hợp lệ, chỉ chấp nhận file .pdf");
        }
        try {
            return extractPdf(file.getBytes());
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            log.error("Lỗi pipeline rule-based: {}", e.getMessage(), e);
            throw new RuntimeException("Lỗi trích xuất rule-based: " + e.getMessage(), e);
        }
    }

    CandidateProfile extractPdf(byte[] pdfBytes) throws Exception {
        long t0 = System.nanoTime();
        PdfTextExtractor.ExtractionResult extraction = pdfTextExtractor.extract(pdfBytes);
        long t1 = System.nanoTime();
        if (extraction.fullText().length() < PdfTextExtractor.MIN_TEXT_CHARS) {
            throw new IllegalArgumentException(
                    "PDF không có text layer đọc được (có thể là file scan) — "
                            + "pipeline rule-based từ chối xử lý, cần OCR hoặc xem xét thủ công");
        }

        SectionDetector.DetectionResult detected = sectionDetector.detect(extraction.blocks());
        long t2 = System.nanoTime();

        Map<CvSection, SectionContent> sections = new EnumMap<>(CvSection.class);
        for (SectionContent s : detected.sections()) {
            sections.put(s.section(), s);
        }
        CandidateProfile profile = mapper.map(sections, detected.openingHeadings());
        long t3 = System.nanoTime();

        CvValidator.ValidationResult result = validator.validate(profile);
        long t4 = System.nanoTime();

        log.info("rule-based extract: {} blocks/{} trang | pdf={}ms layout+section={}ms fields+map={}ms validate={}ms | warnings={}",
                extraction.blocks().size(), extraction.pages(),
                (t1 - t0) / 1_000_000, (t2 - t1) / 1_000_000,
                (t3 - t2) / 1_000_000, (t4 - t3) / 1_000_000,
                result.warnings().size());
        for (String w : result.warnings()) {
            log.warn("rule-based validation: {}", w);
        }
        if (!detected.unknownHeadings().isEmpty()) {
            log.info("rule-based unknown headings (bổ sung từ điển): {}", detected.unknownHeadings());
        }
        return result.profile();
    }

    /** Truy vết một giá trị về block nguồn (phục vụ debug và kiểm thử). */
    public List<TextBlock> debugBlocks(byte[] pdfBytes) throws Exception {
        return pdfTextExtractor.extract(pdfBytes).blocks();
    }
}
