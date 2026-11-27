package recruit.demo.cvtemplate;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.jupiter.api.Test;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.CandidateProfileDto.Experience;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class HtmlPdfRendererTest {

    private final CvHtmlRenderer htmlRenderer = new CvHtmlRenderer();
    private final HtmlPdfRenderer pdfRenderer = new HtmlPdfRenderer();

    private CvTemplateConfig harvardConfig() {
        return CvTemplateConfig.builder()
                .layout("ONE_COLUMN")
                .font("Tinos")
                .accent("#1f1d1a")
                .background("#ffffff")
                .header("CENTER")
                .heading("UPPERCASE_RULE")
                .dates("RIGHT_INLINE")
                .density("COMPACT")
                .margin("NORMAL")
                .sections(List.of("info", "objective", "education", "experience",
                        "projects", "honours", "skills", "languages", "certificates"))
                .build();
    }

    private CvTemplateConfig twoColumnConfig() {
        return CvTemplateConfig.builder()
                .layout("TWO_COLUMN")
                .font("Be Vietnam Pro")
                .accent("#2f4cb8")
                .background("#ffffff")
                .header("LEFT")
                .heading("ACCENT")
                .dates("BELOW")
                .density("NORMAL")
                .margin("NORMAL")
                .sections(List.of("info", "skills", "languages", "certificates",
                        "objective", "experience", "projects", "education", "honours"))
                .build();
    }

    @Test
    void rendersOneColumnHarvardPdfWithVietnameseText() throws IOException {
        CandidateProfileDto profile = SampleCvProfile.create();
        String title = "Kỹ sư phần mềm";
        String xhtml = htmlRenderer.renderHtmlForPdf(harvardConfig(), profile, title);

        byte[] pdf = pdfRenderer.renderPdfFromXhtml(xhtml);
        assertTrue(pdf.length > 1000);

        try (PDDocument doc = Loader.loadPDF(pdf)) {
            assertTrue(doc.getNumberOfPages() >= 1);
            String text = new PDFTextStripper().getText(doc);
            assertTrue(text.contains("Nguyễn Văn Học"), "PDF text should contain Vietnamese full name");
            assertTrue(text.contains("Kỹ sư phần mềm"), "PDF text should contain Vietnamese title");
            assertTrue(text.contains("Học viện Công nghệ Bưu chính Viễn thông"));
            assertTrue(text.contains("Hà Nội"));
        }

        byte[] png = pdfRenderer.renderFirstPagePng(pdf);
        assertTrue(png.length > 500);
        assertEquals((byte) 0x89, png[0]);
        assertEquals((byte) 'P', png[1]);
        assertEquals((byte) 'N', png[2]);
        assertEquals((byte) 'G', png[3]);
    }

    @Test
    void rendersTwoColumnPdfAcrossMultiplePagesWhenContentIsLong() throws IOException {
        CandidateProfileDto profile = SampleCvProfile.create();
        List<Experience> manyExps = new ArrayList<>();
        for (int i = 1; i <= 14; i++) {
            Experience exp = new Experience();
            exp.setCompany("Công ty Phần mềm Số " + i);
            exp.setJob_title("Kỹ sư Backend Cấp cao " + i);
            exp.setLocation("TP. Hồ Chí Minh");
            exp.setStart_date("01/2020");
            exp.setEnd_date("12/2024");
            exp.setDescription(List.of(
                    "Thiết kế kiến trúc microservices chịu tải cao và tối ưu cơ sở dữ liệu quan hệ.",
                    "Phát triển hệ thống xử lý bất đồng bộ với RabbitMQ, Redis và giám sát hiệu năng."
            ));
            manyExps.add(exp);
        }
        profile.setExperience(manyExps);

        String xhtml = htmlRenderer.renderHtmlForPdf(twoColumnConfig(), profile, "Senior Backend Engineer");
        byte[] pdf = pdfRenderer.renderPdfFromXhtml(xhtml);

        try (PDDocument doc = Loader.loadPDF(pdf)) {
            assertTrue(doc.getNumberOfPages() >= 2, "Long CV should span multiple A4 pages");
            String text = new PDFTextStripper().getText(doc);
            assertTrue(text.contains("Nguyễn Văn Học"));
            assertTrue(text.contains("Công ty Phần mềm Số 14"));
        }
    }

    @Test
    void escapesXssScriptTagsInIframeAndPdfHtml() {
        CandidateProfileDto profile = SampleCvProfile.create();
        Experience xssExp = new Experience();
        xssExp.setCompany("<script>alert(1)</script>");
        xssExp.setJob_title("Kỹ sư <img src=x onerror=alert(2)>");
        xssExp.setLocation("Hà Nội");
        xssExp.setStart_date("01/2024");
        xssExp.setEnd_date("Hiện tại");
        profile.setExperience(List.of(xssExp));

        String html = htmlRenderer.renderHtmlForIframe(harvardConfig(), profile, SampleCvProfile.SAMPLE_TITLE);

        assertFalse(html.contains("<script>alert(1)</script>"), "Raw <script> tag must not appear");
        assertTrue(html.contains("&lt;script&gt;alert(1)&lt;/script&gt;"), "Script tag must be HTML-escaped");
        assertFalse(html.contains("<img src=x"), "Raw <img> tag must not appear");
        assertTrue(html.contains("@font-face"), "Iframe preview should embed @font-face");
    }

    @Test
    void rendersAllConfiguredFontsWithVietnameseCharacters() throws IOException {
        CandidateProfileDto profile = SampleCvProfile.create();
        for (String font : CvTemplateOptions.VALID_FONTS) {
            CvTemplateConfig cfg = harvardConfig();
            cfg.setFont(font);
            cfg.setHeading("ACCENT");
            cfg.setDates("BELOW");
            cfg.setMargin("WIDE");
            String xhtml = htmlRenderer.renderHtmlForPdf(cfg, profile, "Kỹ sư phần mềm");
            byte[] pdf = pdfRenderer.renderPdfFromXhtml(xhtml);
            try (PDDocument doc = Loader.loadPDF(pdf)) {
                String text = new PDFTextStripper().getText(doc);
                assertTrue(text.contains("Nguyễn Văn Học"), "Font " + font + " failed Vietnamese check");
            }
        }
    }
}
