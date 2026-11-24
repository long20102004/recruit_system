package recruit.demo.extraction.pdf;

import static org.junit.jupiter.api.Assumptions.assumeTrue;

import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.Test;

/** Prints block geometry (no text) of one PDF: -Dpdf.file=... (local debugging of feature 011). */
class BlockDebugRunner {
    @Test
    void blocks() throws Exception {
        String f = System.getProperty("pdf.file");
        assumeTrue(f != null && !f.isBlank(), "pdf.file not set");
        var r = new PdfTextExtractor().extract(Files.readAllBytes(Path.of(f)));
        for (TextBlock b : r.blocks()) {
            System.out.println("BLOCK " + b);
        }
    }
}
