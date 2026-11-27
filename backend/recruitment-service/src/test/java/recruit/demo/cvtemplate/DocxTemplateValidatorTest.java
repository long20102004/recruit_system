package recruit.demo.cvtemplate;

import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpStatus;
import recruit.demo.exception.ApiException;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.*;

class DocxTemplateValidatorTest {

    private final DocxTemplateValidator validator = new DocxTemplateValidator();

    @Test
    void acceptsValidHarvardSampleDocx() throws IOException {
        ClassPathResource res = new ClassPathResource("cv-templates/harvard-sample.docx");
        assertTrue(res.exists(), "harvard-sample.docx must exist on classpath");
        byte[] bytes = res.getInputStream().readAllBytes();
        assertDoesNotThrow(() -> validator.validate("harvard-sample.docx", bytes));
    }

    @Test
    void rejectsWrongExtensionAndDocm() throws IOException {
        byte[] valid = minimalDocxWithText("{{full_name}}");

        ApiException pdfEx = assertThrows(ApiException.class,
                () -> validator.validate("template.pdf", valid));
        assertEquals(HttpStatus.BAD_REQUEST, pdfEx.getStatus());

        ApiException docmEx = assertThrows(ApiException.class,
                () -> validator.validate("template.docm", valid));
        assertEquals(HttpStatus.BAD_REQUEST, docmEx.getStatus());
    }

    @Test
    void rejectsFileLargerThan2Mb() {
        byte[] huge = new byte[(int) DocxTemplateValidator.MAX_DOCX_BYTES + 1];
        ApiException ex = assertThrows(ApiException.class,
                () -> validator.validate("huge.docx", huge));
        assertEquals(HttpStatus.BAD_REQUEST, ex.getStatus());
        assertTrue(ex.getMessage().contains("2MB"));
    }

    @Test
    void rejectsVbaMacroEntryEvenWithDocxExtension() throws IOException {
        byte[] docxWithMacro = zipWithExtraEntry(minimalDocxWithText("{{full_name}}"),
                "word/vbaProject.bin", "macro".getBytes(StandardCharsets.UTF_8));

        ApiException ex = assertThrows(ApiException.class,
                () -> validator.validate("evil.docx", docxWithMacro));
        assertEquals(HttpStatus.BAD_REQUEST, ex.getStatus());
        assertTrue(ex.getMessage().toLowerCase().contains("macro"));
    }

    @Test
    void rejectsUnsupportedPlaceholderWithTagNameAndLocation() throws IOException {
        byte[] badDocx = minimalDocxWithText("Họ tên: {{full_name}}, lương mong muốn: {{expected_salary}}");

        ApiException ex = assertThrows(ApiException.class,
                () -> validator.validate("bad-tag.docx", badDocx));
        assertEquals(HttpStatus.BAD_REQUEST, ex.getStatus());
        assertTrue(ex.getMessage().contains("expected_salary"), "Should mention invalid tag name");
        assertTrue(ex.getMessage().contains("đoạn #1"), "Should mention location");
    }

    @Test
    void rejectsUnclosedOrMismatchedSectionTags() throws IOException {
        byte[] unclosed = minimalDocxWithText("{{?experience}} {{company}}");
        ApiException ex1 = assertThrows(ApiException.class,
                () -> validator.validate("unclosed.docx", unclosed));
        assertEquals(HttpStatus.BAD_REQUEST, ex1.getStatus());
        assertTrue(ex1.getMessage().contains("experience"));

        byte[] mismatched = minimalDocxWithText("{{?experience}} {{company}} {{/education}}");
        ApiException ex2 = assertThrows(ApiException.class,
                () -> validator.validate("mismatch.docx", mismatched));
        assertEquals(HttpStatus.BAD_REQUEST, ex2.getStatus());
        assertTrue(ex2.getMessage().contains("education"));
    }

    private static byte[] minimalDocxWithText(String text) throws IOException {
        try (XWPFDocument doc = new XWPFDocument();
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            XWPFParagraph p = doc.createParagraph();
            p.createRun().setText(text);
            doc.write(out);
            return out.toByteArray();
        }
    }

    private static byte[] zipWithExtraEntry(byte[] baseZip, String entryName, byte[] entryData) throws IOException {
        try (ByteArrayOutputStream out = new ByteArrayOutputStream();
             ZipOutputStream zos = new ZipOutputStream(out);
             java.util.zip.ZipInputStream zis = new java.util.zip.ZipInputStream(new java.io.ByteArrayInputStream(baseZip))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                zos.putNextEntry(new ZipEntry(entry.getName()));
                zos.write(zis.readAllBytes());
                zos.closeEntry();
            }
            zos.putNextEntry(new ZipEntry(entryName));
            zos.write(entryData);
            zos.closeEntry();
            zos.finish();
            return out.toByteArray();
        }
    }
}
