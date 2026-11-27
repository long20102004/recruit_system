package recruit.demo.cvtemplate;

import org.apache.poi.xwpf.extractor.XWPFWordExtractor;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import recruit.demo.dto.CandidateProfileDto;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class CvDocxRendererTest {

    private final CvDocxRenderer renderer = new CvDocxRenderer();

    @Test
    void fillsSampleProfileIntoHarvardDocxTemplate() throws IOException {
        byte[] templateBytes = new ClassPathResource("cv-templates/harvard-sample.docx")
                .getInputStream().readAllBytes();
        CandidateProfileDto profile = SampleCvProfile.create();

        byte[] rendered = renderer.renderDocx(templateBytes, profile, SampleCvProfile.SAMPLE_TITLE);
        String text = extractText(rendered);

        assertTrue(text.contains("Nguyễn Văn Học"));
        assertTrue(text.contains("hoc.nguyen@hirelens.vn"));
        assertTrue(text.contains("Học viện Công nghệ Bưu chính Viễn thông"));
        assertTrue(text.contains("Công ty Công nghệ HireLens"));
        assertTrue(text.contains("Hệ thống Ghép CV Thông minh"));
        assertTrue(text.contains("Giải Nhì Olympic Tin học Sinh viên Toàn quốc"));
        assertTrue(text.contains("AWS Certified Developer"));
        assertTrue(text.contains("IELTS 7.0"));
        assertFalse(text.contains("{{"), "All template placeholders should be replaced");
    }

    @Test
    void hidesEmptyRepeatingBlocksWhenHonoursAndProjectsAreEmpty() throws IOException {
        byte[] templateBytes = new ClassPathResource("cv-templates/harvard-sample.docx")
                .getInputStream().readAllBytes();
        CandidateProfileDto profile = SampleCvProfile.create();
        profile.setHonours(List.of());
        profile.setPersonal_projects(null);

        byte[] rendered = renderer.renderDocx(templateBytes, profile, SampleCvProfile.SAMPLE_TITLE);
        String text = extractText(rendered);

        assertFalse(text.contains("{{?honours}}"), "Empty honours block tag must be removed");
        assertFalse(text.contains("{{/honours}}"));
        assertFalse(text.contains("{{?projects}}"), "Empty projects block tag must be removed");
        assertFalse(text.contains("{{/projects}}"));
        assertFalse(text.contains("{{value}}"));
        assertFalse(text.contains("Công nghệ:"), "Content inside empty projects block must be hidden");
        assertTrue(text.contains("Nguyễn Văn Học"));
        assertTrue(text.contains("Công ty Công nghệ HireLens"));
    }

    private static String extractText(byte[] docxBytes) throws IOException {
        try (XWPFDocument doc = new XWPFDocument(new ByteArrayInputStream(docxBytes));
             XWPFWordExtractor extractor = new XWPFWordExtractor(doc)) {
            return extractor.getText();
        }
    }
}
