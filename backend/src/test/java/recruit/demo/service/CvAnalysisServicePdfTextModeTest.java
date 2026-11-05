package recruit.demo.service;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import recruit.demo.client.AiServiceClient;
import recruit.demo.dto.AiCvRequest;
import recruit.demo.dto.AiCvResponse;
import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.pdf.PdfTextExtractor;

import java.io.ByteArrayOutputStream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class CvAnalysisServicePdfTextModeTest {
    @Test
    void defaultIsExactlyLegacySortByPosition() throws Exception {
        MockMultipartFile file = pdf();
        CvAnalysisService service = new CvAnalysisService(mock(AiServiceClient.class));
        try (PDDocument document = Loader.loadPDF(file.getBytes())) {
            PDFTextStripper stripper = new PDFTextStripper();
            stripper.setSortByPosition(true);
            assertEquals(stripper.getText(document), service.extractPdfText(file));
        }
    }

    @ParameterizedTest
    @ValueSource(strings = {"legacy", "layout"})
    void previewAndLlmReceiveIdenticalTextInBothModes(String mode) throws Exception {
        AiServiceClient client = mock(AiServiceClient.class);
        AiCvResponse response = mock(AiCvResponse.class);
        CandidateProfile profile = mock(CandidateProfile.class);
        when(response.getData()).thenReturn(profile);
        when(client.extractCv(any())).thenReturn(response);
        CvAnalysisService service = new CvAnalysisService(client);
        ReflectionTestUtils.setField(service, "pdfTextMode", mode);
        MockMultipartFile file = pdf();
        String preview = service.extractPdfText(file);
        assertSame(profile, service.analyzeCvPdf(file));
        ArgumentCaptor<AiCvRequest> request = ArgumentCaptor.forClass(AiCvRequest.class);
        verify(client).extractCv(request.capture());
        assertEquals(preview, request.getValue().getCv_text());
        if ("layout".equals(mode)) {
            assertEquals(new PdfTextExtractor().extract(file.getBytes()).fullText(), preview);
            assertTrue(preview.indexOf("LEFT row3") < preview.indexOf("RIGHT row0"));
        } else {
            assertTrue(preview.indexOf("RIGHT row0") < preview.indexOf("LEFT row3"));
        }
    }

    @Test
    void unknownModeIsNotSilentlyTreatedAsLegacy() throws Exception {
        CvAnalysisService service = new CvAnalysisService(mock(AiServiceClient.class));
        ReflectionTestUtils.setField(service, "pdfTextMode", "typo");
        MockMultipartFile file = pdf();
        assertThrows(IllegalArgumentException.class, () -> service.extractPdfText(file));
    }

    private static MockMultipartFile pdf() throws Exception {
        try (PDDocument document = new PDDocument()) {
            PDPage page = new PDPage();
            document.addPage(page);
            try (PDPageContentStream stream = new PDPageContentStream(document, page)) {
                for (int row = 0; row < 4; row++) {
                    for (int column = 0; column < 2; column++) {
                        stream.beginText();
                        stream.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 10);
                        stream.newLineAtOffset(40 + column * 280, 700 - row * 18);
                        stream.showText((column == 0 ? "LEFT" : "RIGHT") + " row" + row + " synthetic content");
                        stream.endText();
                    }
                }
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.save(out);
            return new MockMultipartFile("file", "synthetic.pdf", "application/pdf", out.toByteArray());
        }
    }
}
