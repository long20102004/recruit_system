package recruit.demo.extraction.docx;

import org.apache.poi.ooxml.POIXMLException;
import org.apache.poi.openxml4j.exceptions.NotOfficeXmlFileException;
import org.apache.poi.xwpf.extractor.XWPFWordExtractor;
import org.apache.poi.xwpf.usermodel.XWPFDocument;

import java.io.ByteArrayInputStream;
import java.io.IOException;

/** Trích xuất văn bản thuần từ tệp Word (.docx), bao gồm đoạn văn, bảng và header/footer. */
public class DocxTextExtractor {

    public String extract(byte[] bytes) throws IOException {
        if (bytes == null || bytes.length == 0) {
            throw new IOException("Empty DOCX content");
        }
        try (XWPFDocument doc = new XWPFDocument(new ByteArrayInputStream(bytes));
             XWPFWordExtractor extractor = new XWPFWordExtractor(doc)) {
            return extractor.getText();
        } catch (POIXMLException | NotOfficeXmlFileException ex) {
            throw new IOException("Invalid DOCX content", ex);
        } catch (RuntimeException ex) {
            throw new IOException("Failed to read DOCX content", ex);
        }
    }
}
