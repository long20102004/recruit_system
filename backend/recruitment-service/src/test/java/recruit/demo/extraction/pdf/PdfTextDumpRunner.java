package recruit.demo.extraction.pdf;

import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

/**
 * Dumps the column-aware text of every PDF in a folder (spec 011 measurement).
 * Skipped unless {@code -Dpdf.dir} is set. Writes {@code <out.dir>/<name>.json} = {"filename","chars","text"}.
 *
 * <pre>mvn -q test -Dtest=PdfTextDumpRunner -Dpdf.dir=../dataset/pdf -Dout.dir=/tmp/out [-Dmode=legacy]</pre>
 * {@code mode=legacy}: PDFTextStripper with sortByPosition (the text the LLM received before feature 011).
 */
class PdfTextDumpRunner {

    @Test
    void dump() throws Exception {
        String dir = System.getProperty("pdf.dir");
        assumeTrue(dir != null && !dir.isBlank(), "pdf.dir not set");
        Path out = Path.of(System.getProperty("out.dir", "pdf-text"));
        Files.createDirectories(out);
        JsonMapper mapper = JsonMapper.builder().build();
        PdfTextExtractor extractor = new PdfTextExtractor();
        boolean legacy = "legacy".equals(System.getProperty("mode"));
        List<Path> pdfs;
        try (Stream<Path> s = Files.list(Path.of(dir))) {
            pdfs = s.filter(p -> p.toString().toLowerCase().endsWith(".pdf")).sorted().toList();
        }
        int ok = 0;
        for (Path pdf : pdfs) {
            String name = pdf.getFileName().toString().replaceAll("(?i)\\.pdf$", "");
            try {
                String text;
                if (legacy) {
                    try (PDDocument doc = Loader.loadPDF(Files.readAllBytes(pdf))) {
                        PDFTextStripper stripper = new PDFTextStripper();
                        stripper.setSortByPosition(true);
                        text = stripper.getText(doc);
                    }
                } else {
                    text = extractor.extract(Files.readAllBytes(pdf)).fullText();
                }
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("filename", pdf.getFileName().toString());
                row.put("chars", text.length());
                row.put("text", text);
                Files.writeString(out.resolve(name + ".json"), mapper.writeValueAsString(row));
                ok++;
            } catch (Exception e) {
                System.out.println("failed " + name + " " + e.getClass().getSimpleName());
            }
        }
        System.out.println("dumped " + ok + "/" + pdfs.size());
    }
}
