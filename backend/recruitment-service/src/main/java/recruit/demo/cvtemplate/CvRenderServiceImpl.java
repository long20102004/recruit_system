package recruit.demo.cvtemplate;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.exception.ApiException;
import recruit.demo.storage.StorageService;

/** Điều phối render CV theo loại mẫu ({@link CvTemplateType#CONFIG} hoặc {@link CvTemplateType#DOCX}). */
@Service
@RequiredArgsConstructor
public class CvRenderServiceImpl implements CvRenderService {

    private final CvHtmlRenderer htmlRenderer;
    private final HtmlPdfRenderer htmlPdfRenderer;
    private final CvDocxRenderer docxRenderer;
    private final GotenbergClient gotenbergClient;
    private final StorageService storageService;

    @Override
    public String renderHtml(CvTemplateConfig config, CandidateProfileDto profile, String cvTitle) {
        return htmlRenderer.renderHtmlForIframe(config, profile, cvTitle);
    }

    @Override
    public byte[] renderConfigPdf(CvTemplateConfig config, CandidateProfileDto profile, String cvTitle) {
        String xhtml = htmlRenderer.renderHtmlForPdf(config, profile, cvTitle);
        return htmlPdfRenderer.renderPdfFromXhtml(xhtml);
    }

    @Override
    public byte[] renderDocxPdf(byte[] docxBytes, CandidateProfileDto profile, String cvTitle) {
        byte[] filledDocx = docxRenderer.renderDocx(docxBytes, profile, cvTitle);
        return gotenbergClient.convertDocxToPdf(filledDocx);
    }

    @Override
    public byte[] renderPdf(CvTemplate template, CandidateProfileDto profile, String cvTitle) {
        if (template == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Không tìm thấy mẫu CV để xuất PDF");
        }
        if (template.getType() == CvTemplateType.DOCX) {
            if (template.getDocxKey() == null || template.getDocxKey().isBlank()) {
                throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Mẫu Word thiếu file gốc");
            }
            byte[] docxBytes = storageService.getPrivate(template.getDocxKey());
            return renderDocxPdf(docxBytes, profile, cvTitle);
        }
        return renderConfigPdf(template.getConfig(), profile, cvTitle);
    }

    @Override
    public byte[] renderFirstPagePng(byte[] pdfBytes) {
        return htmlPdfRenderer.renderFirstPagePng(pdfBytes);
    }
}
