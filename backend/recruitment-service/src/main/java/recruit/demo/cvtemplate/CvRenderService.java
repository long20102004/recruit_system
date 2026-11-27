package recruit.demo.cvtemplate;

import recruit.demo.dto.CandidateProfileDto;

/** Dịch vụ render CV theo mẫu CONFIG (HTML/PDF) hoặc DOCX (poi-tl + Gotenberg -> PDF). */
public interface CvRenderService {

    String renderHtml(CvTemplateConfig config, CandidateProfileDto profile, String cvTitle);

    byte[] renderConfigPdf(CvTemplateConfig config, CandidateProfileDto profile, String cvTitle);

    byte[] renderDocxPdf(byte[] docxBytes, CandidateProfileDto profile, String cvTitle);

    byte[] renderPdf(CvTemplate template, CandidateProfileDto profile, String cvTitle);

    byte[] renderFirstPagePng(byte[] pdfBytes);
}
