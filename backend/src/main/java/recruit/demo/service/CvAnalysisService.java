package recruit.demo.service;

import recruit.demo.client.AiServiceClient;
import recruit.demo.dto.AiCvRequest;
import recruit.demo.dto.AiCvResponse;
import recruit.demo.dto.CandidateProfile;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@Service
@RequiredArgsConstructor
@Slf4j
public class CvAnalysisService {

    private final AiServiceClient aiServiceClient;

    public CandidateProfile analyzeCv(String rawCvText) {
        if (rawCvText == null || rawCvText.trim().isEmpty()) {
            throw new IllegalArgumentException("Văn bản CV không được để trống");
        }

        AiCvRequest request = new AiCvRequest();
        request.setCv_text(rawCvText);

        AiCvResponse response = aiServiceClient.extractCv(request);
        
        if (response != null && response.getData() != null) {
            return response.getData();
        }
        
        throw new RuntimeException("Không thể trích xuất thông tin CV từ AI Service");
    }

    public CandidateProfile analyzeCvPdf(MultipartFile file) {
        validatePdfFile(file);

        String extractedText = extractTextFromPdf(file);
        if (extractedText == null || extractedText.trim().isEmpty()) {
            throw new RuntimeException("Không thể trích xuất nội dung văn bản từ file PDF (có thể là file ảnh scan hoặc file rỗng)");
        }

        log.info("Trích xuất thành công {} ký tự từ file PDF: {}", extractedText.length(), file.getOriginalFilename());
        return analyzeCv(extractedText);
    }

    /**
     * Chỉ trích xuất text từ PDF, không gọi AI.
     * Dùng để kiểm tra/preview nội dung PDF trước khi analyze.
     */
    public String extractPdfText(MultipartFile file) {
        validatePdfFile(file);

        String extractedText = extractTextFromPdf(file);
        if (extractedText == null || extractedText.trim().isEmpty()) {
            throw new RuntimeException("Không thể trích xuất nội dung văn bản từ file PDF (có thể là file ảnh scan hoặc file rỗng)");
        }

        log.info("Trích xuất thành công {} ký tự từ file PDF: {}", extractedText.length(), file.getOriginalFilename());
        return extractedText;
    }

    private void validatePdfFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("File PDF không được để trống");
        }

        String fileName = file.getOriginalFilename();
        if (fileName != null && !fileName.toLowerCase().endsWith(".pdf")) {
            throw new IllegalArgumentException("Định dạng file không hợp lệ, chỉ chấp nhận file .pdf");
        }
    }

    public String extractTextFromPdf(MultipartFile file) {
        try (PDDocument document = Loader.loadPDF(file.getBytes())) {
            PDFTextStripper stripper = new PDFTextStripper();
            stripper.setSortByPosition(true);
            return stripper.getText(document);
        } catch (IOException e) {
            log.error("Lỗi khi đọc file PDF: {}", e.getMessage(), e);
            throw new IllegalArgumentException("File không phải PDF hợp lệ: " + e.getMessage(), e);
        }
    }
}
