package recruit.demo.service.cv;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.http.HttpStatus;
import recruit.demo.client.AiJsonClient;
import recruit.demo.exception.ApiException;
import recruit.demo.extraction.pdf.PdfTextExtractor;
import tools.jackson.databind.JsonNode;
import java.io.IOException;
import java.util.Map;
@Service
public class CvExtractionModule {
    private final AiJsonClient http;
    private final String url;
    public CvExtractionModule(AiJsonClient http, @Value("${app.cv-extraction.base-url}") String url) {
        this.http = http; this.url = url;
    }
    public JsonNode extract(byte[] pdf) {
        String text;
        try { text = new PdfTextExtractor().extract(pdf).fullText(); }
        catch (IOException | IllegalArgumentException ex) { throw new ApiException(HttpStatus.BAD_REQUEST, "Invalid PDF or too many pages"); }
        if (text == null || text.strip().length() < PdfTextExtractor.MIN_TEXT_CHARS)
            throw new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, "PDF has no readable text; OCR is required for scanned CVs");
        var response = http.post(url + "/api/v1/extract-cv?include=kg", Map.of("cv_text", text));
        var data = response.get("data");
        if (data == null || !data.isObject() || data.isEmpty())
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Extraction service returned no profile");
        return data;
    }
}
