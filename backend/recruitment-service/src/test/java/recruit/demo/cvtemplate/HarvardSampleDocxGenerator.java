package recruit.demo.cvtemplate;

import org.apache.poi.xwpf.usermodel.*;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageSz;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSectPr;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;

/** Generator tạo file Word mẫu bố cục Harvard ({@code resources/cv-templates/harvard-sample.docx}). */
public final class HarvardSampleDocxGenerator {

    private static final String FONT_NAME = "Liberation Serif";

    private HarvardSampleDocxGenerator() {
    }

    public static byte[] generateBytes() throws IOException {
        try (XWPFDocument doc = new XWPFDocument();
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {

            CTSectPr sectPr = doc.getDocument().getBody().addNewSectPr();
            CTPageSz pageSz = sectPr.addNewPgSz();
            pageSz.setW(BigInteger.valueOf(11906));
            pageSz.setH(BigInteger.valueOf(16838));
            var mar = sectPr.addNewPgMar();
            mar.setTop(BigInteger.valueOf(794));
            mar.setBottom(BigInteger.valueOf(794));
            mar.setLeft(BigInteger.valueOf(794));
            mar.setRight(BigInteger.valueOf(794));

            // Header
            addCenteredParagraph(doc, "{{full_name}}", 18, true, "1F1D1A", 20);
            addCenteredParagraph(doc, "{{title}}", 11, false, "44403C", 20);
            addCenteredParagraph(doc, "{{email}}  |  {{phone}}  |  {{github}}", 9, false, "57534E", 100);

            // Objective
            addSectionHeading(doc, "MỤC TIÊU NGHỀ NGHIỆP");
            addBodyParagraph(doc, "{{objective}}", false, 60);

            // Education
            addSectionHeading(doc, "HỌC VẤN");
            addBodyParagraph(doc, "{{?education}}", false, 0);
            addBodyParagraph(doc, "{{school}} — {{location}}  ({{start_year}} - {{end_year}})", true, 20);
            addBodyParagraph(doc, "{{major}} | GPA: {{gpa}}", false, 60);
            addBodyParagraph(doc, "{{/education}}", false, 0);

            // Experience
            addSectionHeading(doc, "KINH NGHIỆM LÀM VIỆC");
            addBodyParagraph(doc, "{{?experience}}", false, 0);
            addBodyParagraph(doc, "{{job_title}} — {{company}}, {{location}}  ({{start_date}} - {{end_date}})", true, 20);
            addBodyParagraph(doc, "{{description}}", false, 60);
            addBodyParagraph(doc, "{{/experience}}", false, 0);

            // Projects
            addSectionHeading(doc, "DỰ ÁN CÁ NHÂN");
            addBodyParagraph(doc, "{{?projects}}", false, 0);
            addBodyParagraph(doc, "{{name}} — {{role}}  ({{start_date}} - {{end_date}}) | Quy mô: {{team_size}}", true, 20);
            addBodyParagraph(doc, "Công nghệ: {{tech_stack}} | {{github_url}}", false, 20);
            addBodyParagraph(doc, "{{description}}", false, 60);
            addBodyParagraph(doc, "{{/projects}}", false, 0);

            // Honours
            addSectionHeading(doc, "GIẢI THƯỞNG & HOẠT ĐỘNG");
            addBodyParagraph(doc, "{{?honours}}", false, 0);
            addBodyParagraph(doc, "• {{value}}", false, 20);
            addBodyParagraph(doc, "{{/honours}}", false, 0);

            // Skills
            addSectionHeading(doc, "KỸ NĂNG");
            addBodyParagraph(doc, "{{?skills}}", false, 0);
            addBodyParagraph(doc, "• {{value}}", false, 20);
            addBodyParagraph(doc, "{{/skills}}", false, 0);

            // Languages
            addSectionHeading(doc, "NGOẠI NGỮ");
            addBodyParagraph(doc, "{{?languages}}", false, 0);
            addBodyParagraph(doc, "• {{language}}: {{note}}", false, 20);
            addBodyParagraph(doc, "{{/languages}}", false, 0);

            // Certificates
            addSectionHeading(doc, "CHỨNG CHỈ");
            addBodyParagraph(doc, "{{?certificates}}", false, 0);
            addBodyParagraph(doc, "• {{value}}", false, 20);
            addBodyParagraph(doc, "{{/certificates}}", false, 0);

            doc.write(out);
            return out.toByteArray();
        }
    }

    private static void addCenteredParagraph(XWPFDocument doc, String text, int fontSize, boolean bold, String colorHex, int spaceAfter) {
        XWPFParagraph p = doc.createParagraph();
        p.setAlignment(ParagraphAlignment.CENTER);
        p.setSpacingAfter(spaceAfter);
        XWPFRun run = p.createRun();
        run.setFontFamily(FONT_NAME);
        run.setFontSize(fontSize);
        run.setBold(bold);
        run.setColor(colorHex);
        run.setText(text);
    }

    private static void addSectionHeading(XWPFDocument doc, String title) {
        XWPFParagraph p = doc.createParagraph();
        p.setSpacingBefore(120);
        p.setSpacingAfter(40);
        p.setBorderBottom(Borders.SINGLE);
        XWPFRun run = p.createRun();
        run.setFontFamily(FONT_NAME);
        run.setFontSize(11);
        run.setBold(true);
        run.setColor("1F1D1A");
        run.setText(title);
    }

    private static void addBodyParagraph(XWPFDocument doc, String text, boolean bold, int spaceAfter) {
        XWPFParagraph p = doc.createParagraph();
        p.setSpacingAfter(spaceAfter);
        XWPFRun run = p.createRun();
        run.setFontFamily(FONT_NAME);
        run.setFontSize(10);
        run.setBold(bold);
        run.setColor("1F1D1A");
        run.setText(text);
    }

    public static void main(String[] args) throws IOException {
        Path target = Path.of("backend/recruitment-service/src/main/resources/cv-templates/harvard-sample.docx");
        Files.createDirectories(target.getParent());
        Files.write(target, generateBytes());
        System.out.println("Generated " + target.toAbsolutePath());
    }
}
