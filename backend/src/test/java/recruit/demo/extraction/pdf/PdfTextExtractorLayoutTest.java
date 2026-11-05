package recruit.demo.extraction.pdf;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import recruit.demo.extraction.service.RuleBasedCvExtractionService;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.*;

/** Only generated, anonymous PDF content: no real CV fixtures. */
class PdfTextExtractorLayoutTest {
    private record Text(float x, float y, String value) { }

    @Test
    void spanningHeaderThenAlignedColumnsOutsideFixedHeaderZone() throws Exception {
        List<Text> page = new ArrayList<>();
        page.add(new Text(40, 180, "HEADER spanning the entire width of both synthetic text columns for reading order"));
        page.addAll(columns(2, "P1", 240));
        byte[] pdf = pdf(List.of(page));
        PdfTextExtractor.ExtractionResult result = new PdfTextExtractor().extract(pdf);
        List<String> expected = new ArrayList<>();
        expected.add(page.getFirst().value());
        expected.addAll(expectedColumns(2, "P1"));
        assertEquals(expected, lines(result.fullText()));
        assertEquals(1, result.pages());
        assertEquals(result.blocks(), new RuleBasedCvExtractionService().debugBlocks(pdf));
        for (int i = 0; i < result.blocks().size(); i++) {
            TextBlock block = result.blocks().get(i);
            assertEquals(i, block.order());
            assertEquals(1, block.page());
            assertTrue(block.x1() > block.x0());
            assertTrue(block.y1() > block.y0());
        }
    }

    @Test
    void rightAlignedDatesStayOnCompanyRows() throws Exception {
        List<Text> page = new ArrayList<>();
        List<String> expected = new ArrayList<>();
        for (int i = 0; i < 4; i++) {
            String company = "Company ABC synthetic engineering " + i;
            page.add(new Text(40, 140 + i * 18, company));
            page.add(new Text(470, 140 + i * 18, "2020 - 2022"));
            expected.add(company + " 2020 - 2022");
        }
        assertEquals(expected, lines(new PdfTextExtractor().extract(pdf(List.of(page))).fullText()));
    }

    @Test
    void narrowTimelineDatesStayOnContentRows() throws Exception {
        List<Text> page = new ArrayList<>();
        List<String> expected = new ArrayList<>();
        String[] dates = {"09/2018", "01/2022", "03/2023", "04/2024"};
        for (int i = 0; i < dates.length; i++) {
            String content = "NETWORK ADMINISTRATOR synthetic position " + i;
            page.add(new Text(40, 140 + i * 18, dates[i]));
            page.add(new Text(130, 140 + i * 18, content));
            expected.add(dates[i] + " " + content);
        }
        assertEquals(expected, lines(new PdfTextExtractor().extract(pdf(List.of(page))).fullText()));
    }

    @Test
    void threeColumnsReadLeftToRight() throws Exception {
        assertEquals(expectedColumns(3, "P1"), lines(new PdfTextExtractor()
                .extract(pdf(List.of(columns(3, "P1", 80)))).fullText()));
    }

    @Test
    void eachPageHasIndependentColumnOrder() throws Exception {
        PdfTextExtractor.ExtractionResult result = new PdfTextExtractor().extract(pdf(List.of(
                columns(2, "P1", 80), columns(2, "P2", 80))));
        List<String> expected = new ArrayList<>(expectedColumns(2, "P1"));
        expected.addAll(expectedColumns(2, "P2"));
        assertEquals(expected, lines(result.fullText()));
        assertEquals(2, result.pages());
        List<Integer> blockPages = result.blocks().stream().map(TextBlock::page).toList();
        assertEquals(List.of(1, 2), blockPages.stream().distinct().toList());
        assertEquals(blockPages.stream().sorted().toList(), blockPages);
        for (int i = 0; i < result.blocks().size(); i++) assertEquals(i, result.blocks().get(i).order());
    }

    @Test
    void spanningSectionSeparatesTwoColumnRegionsRecursively() throws Exception {
        List<Text> page = new ArrayList<>(columns(2, "TOP", 80));
        String heading = "SECTION spanning the entire width of both synthetic text columns for reading order";
        page.add(new Text(40, 200, heading));
        page.addAll(columns(2, "BOTTOM", 260));
        List<String> expected = new ArrayList<>(expectedColumns(2, "TOP"));
        expected.add(heading);
        expected.addAll(expectedColumns(2, "BOTTOM"));
        assertEquals(expected, lines(new PdfTextExtractor().extract(pdf(List.of(page))).fullText()));
    }

    @Test
    void preservesExplicitSpacesAndSpacedLetters() throws Exception {
        byte[] pdf = pdf(List.of(List.of(new Text(40, 80, "Skills Java Spring PDFBox"),
                new Text(40, 98, "A B C explicit spaces"))));
        assertEquals(List.of("Skills Java Spring PDFBox", "A B C explicit spaces"),
                lines(new PdfTextExtractor().extract(pdf).fullText()));
    }

    @Test
    void layoutWordsMatchLegacyAcrossSyntheticLayouts() throws Exception {
        List<Text> dates = new ArrayList<>();
        for (int i = 0; i < 4; i++) {
            dates.add(new Text(40, 140 + i * 18, "Company synthetic engineering " + i));
            dates.add(new Text(470, 140 + i * 18, "2020 - 2022"));
        }
        List<List<List<Text>>> fixtures = List.of(
                List.of(columns(2, "P1", 80)),
                List.of(columns(3, "P1", 80)),
                List.of(columns(2, "P1", 80), columns(2, "P2", 80)),
                List.of(dates),
                List.of(List.of(new Text(40, 80, "Skills Java Spring PDFBox"),
                        new Text(40, 98, "A B C explicit spaces"))));
        for (List<List<Text>> fixture : fixtures) {
            assertWordsMatchLegacy(pdf(fixture));
        }
    }

    @Test
    void separatelyPositionedWordsWithNarrowGapsMatchLegacy() throws Exception {
        List<List<Text>> pages = List.of(List.of(
                new Text(40, 80, "Skills Java Spring PDFBox"),
                new Text(40, 98, "Experienced engineer builds reliable distributed services"),
                new Text(40, 116, "Narrow word gaps must never concatenate these tokens")));
        byte[] pdf = pdf(pages, true);
        assertWordsMatchLegacy(pdf);
        List<String> expected = pages.getFirst().stream().map(Text::value).toList();
        // Check the fixture itself: legacy must recognize the absent space glyphs.
        assertEquals(expected, lines(legacy(pdf)));
        assertEquals(expected, lines(new PdfTextExtractor().extract(pdf).fullText()));
    }

    @Test
    void thirtySingleColumnRowsWithBulletsAndRightDatesKeepLegacyOrder() throws Exception {
        List<Text> page = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            float y = 60 + i * 22;
            page.add(new Text(40, y, (i % 3 == 0 ? "\u2022 " : "")
                    + "Engineering row " + i + " delivered reliable synthetic services"));
            if (i % 3 == 0) page.add(new Text(470, y, "2020 - 2022"));
        }
        byte[] pdf = pdf(List.of(page));
        assertWordsMatchLegacy(pdf);
        List<String> expected = lines(TextNormalizer.normalize(legacy(pdf)));
        assertEquals(30, expected.size());
        assertEquals(expected, lines(new PdfTextExtractor().extract(pdf).fullText()));
    }

    private static String legacy(byte[] pdf) throws Exception {
        try (PDDocument document = Loader.loadPDF(pdf)) {
            PDFTextStripper stripper = new PDFTextStripper();
            stripper.setSortByPosition(true);
            return stripper.getText(document);
        }
    }

    private static Map<String, Long> words(String text) {
        return Pattern.compile("\\w+").matcher(text).results()
                .collect(Collectors.groupingBy(match -> match.group(), Collectors.counting()));
    }

    private static void assertWordsMatchLegacy(byte[] pdf) throws Exception {
        Map<String, Long> expected = words(legacy(pdf));
        Map<String, Long> actual = words(new PdfTextExtractor().extract(pdf).fullText());
        assertEquals(expected.keySet(), actual.keySet(), "Layout must preserve legacy word boundaries");
        assertEquals(expected, actual, "Layout must also preserve word occurrences");
    }

    @Test
    void emptyPageAndPageLimitKeepExistingContract() throws Exception {
        assertTrue(new PdfTextExtractor().extract(pdf(List.of(List.of()))).blocks().isEmpty());
        List<List<Text>> pages = new ArrayList<>();
        for (int i = 0; i <= PdfTextExtractor.MAX_PAGES; i++) pages.add(List.of());
        assertThrows(IllegalArgumentException.class, () -> new PdfTextExtractor().extract(pdf(pages)));
    }

    @Test
    void ruleBasedPipelineStillAcceptsSyntheticTextLayer() throws Exception {
        byte[] pdf = pdf(List.of(List.of(
                new Text(40, 80, "SYNTHETIC CANDIDATE"),
                new Text(40, 98, "test@example.invalid 0912345678"),
                new Text(40, 140, "SKILLS"),
                new Text(40, 158, "Java, Spring Boot, SQL, Docker"))));
        assertNotNull(new RuleBasedCvExtractionService().extractPdf(
                new MockMultipartFile("file", "synthetic.pdf", "application/pdf", pdf)));
    }

    private static List<Text> columns(int count, String prefix, float y) {
        List<Text> out = new ArrayList<>();
        // Deliberately reversed content-stream order, with aligned baselines.
        for (int row = 0; row < 4; row++) {
            for (int column = count - 1; column >= 0; column--) {
                out.add(new Text(40 + column * (count == 3 ? 180 : 280), y + row * 18,
                        label(prefix, column, row)));
            }
        }
        return out;
    }

    private static String label(String prefix, int column, int row) {
        return prefix + " C" + column + " row" + row + " synthetic content";
    }

    private static List<String> expectedColumns(int count, String prefix) {
        List<String> expected = new ArrayList<>();
        for (int column = 0; column < count; column++) {
            for (int row = 0; row < 4; row++) expected.add(label(prefix, column, row));
        }
        return expected;
    }

    private static List<String> lines(String text) {
        return text.lines().filter(s -> !s.isBlank()).toList();
    }

    private static byte[] pdf(List<List<Text>> pages) throws Exception {
        return pdf(pages, false);
    }

    private static byte[] pdf(List<List<Text>> pages, boolean separateWords) throws Exception {
        try (PDDocument document = new PDDocument()) {
            PDType1Font font = new PDType1Font(Standard14Fonts.FontName.HELVETICA);
            for (List<Text> texts : pages) {
                PDPage page = new PDPage();
                document.addPage(page);
                try (PDPageContentStream stream = new PDPageContentStream(document, page)) {
                    for (Text text : texts) {
                        stream.beginText();
                        stream.setFont(font, 10);
                        stream.newLineAtOffset(text.x(), page.getMediaBox().getHeight() - text.y());
                        if (separateWords) {
                            // No space characters in the content stream: only 0.25em offsets.
                            for (String word : text.value().split(" ")) {
                                stream.showText(word);
                                stream.newLineAtOffset(font.getStringWidth(word) / 1000f * 10 + 2.5f, 0);
                            }
                        } else {
                            stream.showText(text.value());
                        }
                        stream.endText();
                    }
                }
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.save(out);
            return out.toByteArray();
        }
    }
}
