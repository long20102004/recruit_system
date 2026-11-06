package recruit.demo.extraction.service;

import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDFont;
import org.apache.pdfbox.pdmodel.font.PDType0Font;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Evaluation runner (not a unit test): renders each CV text of a JSONL split to a simple PDF
 * (heading-like lines bold and larger) and runs the rule-based pipeline on it.
 * Skipped unless {@code -Deval.in} is set. Output: predictions.jsonl in the ai-service eval format.
 *
 * <pre>mvn -q test -Dtest=RuleBasedEvalRunner -Deval.in=val.jsonl -Deval.out=predictions.jsonl -Deval.font=/path/Regular.ttf -Deval.fontBold=/path/Bold.ttf</pre>
 */
class RuleBasedEvalRunner {

    private static final float MARGIN = 50, BODY = 10, HEAD = 13, LEADING = 1.35f;

    @Test
    void run() throws Exception {
        String in = System.getProperty("eval.in");
        assumeTrue(in != null && !in.isBlank(), "eval.in not set");
        Path out = Path.of(System.getProperty("eval.out", "predictions.jsonl"));
        File regular = new File(System.getProperty("eval.font"));
        File bold = new File(System.getProperty("eval.fontBold"));

        JsonMapper mapper = JsonMapper.builder().build();
        RuleBasedCvExtractionService service = new RuleBasedCvExtractionService();
        List<String> lines = Files.readAllLines(Path.of(in), StandardCharsets.UTF_8);
        List<String> outLines = new ArrayList<>();
        for (String line : lines) {
            if (line.isBlank()) continue;
            JsonNode row = mapper.readTree(line);
            String id = row.get("id").asString();
            String text = row.get("input").asString();
            Map<String, Object> rec = new LinkedHashMap<>();
            rec.put("id", id);
            long t0 = System.nanoTime();
            try {
                byte[] pdf = render(text, regular, bold);
                long t1 = System.nanoTime();
                Object profile = service.extractPdf(pdf);
                rec.put("status", 200);
                rec.put("latency_s", (System.nanoTime() - t1) / 1e9);
                rec.put("data", profile);
            } catch (Exception e) {
                rec.put("status", 500);
                rec.put("latency_s", (System.nanoTime() - t0) / 1e9);
                rec.put("error", e.getClass().getSimpleName());
                Throwable c = e.getCause() != null ? e.getCause() : e;
                rec.put("where", c.getStackTrace().length > 0 ? c.getStackTrace()[0].toString() : "");
                rec.put("where2", c.getStackTrace().length > 3 ? c.getStackTrace()[1] + " | " + c.getStackTrace()[2] + " | " + c.getStackTrace()[3] : "");
                rec.put("data", null);
            }
            outLines.add(mapper.writeValueAsString(rec));
        }
        Files.write(out, outLines, StandardCharsets.UTF_8);
    }

    static boolean isHeading(String s) {
        String t = s.strip().replaceAll("^[#=*\\s]+|[#=*:\\s]+$", "");
        if (t.isEmpty() || t.length() > 45 || s.strip().startsWith("-") || s.strip().startsWith("•")) return false;
        if (s.strip().startsWith("#")) return true;
        long letters = t.chars().filter(Character::isLetter).count();
        long upper = t.chars().filter(Character::isUpperCase).count();
        return letters >= 3 && upper >= letters * 0.8;
    }

    static byte[] render(String text, File regularFile, File boldFile) throws Exception {
        try (PDDocument doc = new PDDocument()) {
            PDFont regular = PDType0Font.load(doc, regularFile);
            PDFont bold = PDType0Font.load(doc, boldFile);
            float width = PDRectangle.A4.getWidth() - 2 * MARGIN;
            PDPageContentStream cs = null;
            float y = 0;
            for (String raw : text.split("\n", -1)) {
                boolean head = isHeading(raw);
                PDFont font = head ? bold : regular;
                float size = head ? HEAD : BODY;
                // Strip markdown markup that a real PDF would render as styling (bold/italic/code), keep bullets.
                String clean = raw.replace("\t", "    ").replaceAll("^[#=]+\\s*", "")
                        .replaceAll("^(\\s*)[*+]\\s+", "$1• ").replaceAll("[*`]+", "").replaceAll("^-{3,}$", "");
                for (String piece : wrap(clean, font, size, width)) {
                    if (cs == null || y < MARGIN + size) {
                        if (cs != null) cs.close();
                        PDPage page = new PDPage(PDRectangle.A4);
                        doc.addPage(page);
                        cs = new PDPageContentStream(doc, page);
                        y = PDRectangle.A4.getHeight() - MARGIN;
                    }
                    y -= size * LEADING;
                    if (!piece.isBlank()) {
                        cs.beginText();
                        cs.setFont(font, size);
                        cs.newLineAtOffset(MARGIN, y);
                        cs.showText(safe(piece, font));
                        cs.endText();
                    }
                }
            }
            if (cs != null) cs.close();
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            doc.save(bos);
            return bos.toByteArray();
        }
    }

    /** Drop characters the font cannot encode (emoji etc.). */
    private static String safe(String s, PDFont font) {
        StringBuilder sb = new StringBuilder();
        s.codePoints().forEach(cp -> {
            String ch = new String(Character.toChars(cp));
            try {
                font.encode(ch);
                sb.append(ch);
            } catch (Exception ignored) {
                // not encodable
            }
        });
        return sb.toString();
    }

    private static List<String> wrap(String line, PDFont font, float size, float width) throws Exception {
        List<String> out = new ArrayList<>();
        if (line.isBlank()) {
            out.add("");
            return out;
        }
        StringBuilder cur = new StringBuilder();
        for (String word : line.split(" ")) {
            String trial = cur.isEmpty() ? word : cur + " " + word;
            if (font.getStringWidth(safe(trial, font)) / 1000 * size > width && !cur.isEmpty()) {
                out.add(cur.toString());
                cur = new StringBuilder(word);
            } else {
                cur = new StringBuilder(trial);
            }
        }
        out.add(cur.toString());
        return out;
    }
}
