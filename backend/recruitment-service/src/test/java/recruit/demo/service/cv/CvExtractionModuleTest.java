package recruit.demo.service.cv;
import org.junit.jupiter.api.Test;
import org.apache.pdfbox.pdmodel.*;
import org.apache.pdfbox.pdmodel.font.*;
import recruit.demo.client.AiJsonClient;
import tools.jackson.databind.*;
import java.io.ByteArrayOutputStream;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
class CvExtractionModuleTest {
    @Test void readablePdfReachesExtractionApiAndReturnsStructuredProfile() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        AiJsonClient fake = new AiJsonClient(mapper) {
            @Override public JsonNode post(String url, Object body) {
                assertEquals("http://extract/api/v1/extract-cv?include=kg", url);
                assertTrue(((Map<?,?>)body).get("cv_text").toString().contains("Java Spring Boot"));
                return mapper.readTree("{\"data\":{\"skills\":[\"Java\"]}}");
            }
        };
        byte[] bytes;
        try (PDDocument doc = new PDDocument(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            PDPage page = new PDPage(); doc.addPage(page);
            try (PDPageContentStream content = new PDPageContentStream(doc, page)) {
                content.beginText(); content.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 12);
                content.newLineAtOffset(30, 700);
                content.showText("Test Candidate with experience in Java Spring Boot MySQL Docker and REST API development.");
                content.endText();
            }
            doc.save(out); bytes = out.toByteArray();
        }
        assertEquals("Java", new CvExtractionModule(fake, "http://extract").extract(bytes).path("skills").get(0).asString());
    }
    @Test void scanLikePdfRequestsOcrInsteadOfCallingModel() throws Exception {
        byte[] bytes;
        try (PDDocument doc = new PDDocument(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            doc.addPage(new PDPage()); doc.save(out); bytes = out.toByteArray();
        }
        var module = new CvExtractionModule(null, "http://unused");
        byte[] pdf = bytes;
        var error = assertThrows(recruit.demo.exception.ApiException.class, () -> module.extract(pdf));
        assertEquals(422, error.getStatus().value());
    }
}
