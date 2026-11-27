package recruit.demo.cvtemplate;

import com.lowagie.text.DocumentException;
import com.lowagie.text.pdf.BaseFont;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.xhtmlrenderer.pdf.ITextFontResolver;
import org.xhtmlrenderer.pdf.ITextRenderer;
import recruit.demo.exception.ApiException;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Chuyển XHTML (từ {@link CvHtmlRenderer}) sang PDF A4 bằng Flying Saucer với font TTF nhúng UTF-8,
 * và xuất ảnh thu nhỏ PNG trang đầu tiên bằng PDFBox 3.
 */
@Component
public class HtmlPdfRenderer {

    private static final float THUMBNAIL_DPI = 120f;

    private static final List<FontAsset> FONT_ASSETS = List.of(
            new FontAsset("Tinos", "fonts/Tinos-Regular.ttf"),
            new FontAsset("Tinos", "fonts/Tinos-Bold.ttf"),
            new FontAsset("Tinos", "fonts/Tinos-Italic.ttf"),
            new FontAsset("Be Vietnam Pro", "fonts/BeVietnamPro-Regular.ttf"),
            new FontAsset("Be Vietnam Pro", "fonts/BeVietnamPro-Bold.ttf"),
            new FontAsset("Be Vietnam Pro", "fonts/BeVietnamPro-Italic.ttf"),
            new FontAsset("Inter", "fonts/Inter-Regular.ttf"),
            new FontAsset("Inter", "fonts/Inter-Bold.ttf"),
            new FontAsset("EB Garamond", "fonts/EBGaramond-Regular.ttf"),
            new FontAsset("EB Garamond", "fonts/EBGaramond-Bold.ttf"),
            new FontAsset("EB Garamond", "fonts/EBGaramond-Italic.ttf"),
            new FontAsset("Noto Serif", "fonts/NotoSerif-Regular.ttf"),
            new FontAsset("Noto Serif", "fonts/NotoSerif-Bold.ttf"),
            new FontAsset("Noto Serif", "fonts/NotoSerif-Italic.ttf")
    );

    private final List<ResolvedFont> resolvedFonts;

    public HtmlPdfRenderer() {
        this.resolvedFonts = extractFontsToTemp();
    }

    public byte[] renderPdfFromXhtml(String xhtml) {
        if (xhtml == null || xhtml.isBlank()) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Nội dung HTML rỗng khi tạo PDF");
        }
        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            ITextRenderer renderer = new ITextRenderer();
            registerFonts(renderer.getFontResolver());
            renderer.setDocumentFromString(xhtml);
            renderer.layout();
            renderer.createPDF(out);
            return out.toByteArray();
        } catch (IOException | RuntimeException ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "Không thể xuất PDF từ mẫu CV: " + ex.getMessage());
        }
    }

    public byte[] renderFirstPagePng(byte[] pdfBytes) {
        if (pdfBytes == null || pdfBytes.length == 0) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "PDF rỗng, không thể tạo ảnh thu nhỏ");
        }
        try (PDDocument doc = Loader.loadPDF(pdfBytes);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            if (doc.getNumberOfPages() == 0) {
                throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "PDF không có trang nào");
            }
            PDFRenderer pdfRenderer = new PDFRenderer(doc);
            BufferedImage image = pdfRenderer.renderImageWithDPI(0, THUMBNAIL_DPI);
            ImageIO.write(image, "PNG", out);
            return out.toByteArray();
        } catch (ApiException ex) {
            throw ex;
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "Không thể tạo ảnh thu nhỏ từ PDF: " + ex.getMessage());
        }
    }

    private void registerFonts(ITextFontResolver resolver) throws DocumentException, IOException {
        for (ResolvedFont font : resolvedFonts) {
            resolver.addFont(
                    font.filePath().toAbsolutePath().toString(),
                    font.family(),
                    BaseFont.IDENTITY_H,
                    BaseFont.EMBEDDED,
                    null
            );
        }
    }

    private static List<ResolvedFont> extractFontsToTemp() {
        try {
            Path tempDir = Files.createTempDirectory("hirelens-cv-fonts-");
            tempDir.toFile().deleteOnExit();
            List<ResolvedFont> result = new ArrayList<>();
            for (FontAsset asset : FONT_ASSETS) {
                ClassPathResource resource = new ClassPathResource(asset.classpath());
                if (!resource.exists()) {
                    continue;
                }
                String fileName = Path.of(asset.classpath()).getFileName().toString();
                Path target = tempDir.resolve(fileName);
                try (InputStream is = resource.getInputStream()) {
                    Files.copy(is, target);
                }
                target.toFile().deleteOnExit();
                result.add(new ResolvedFont(asset.family(), target));
            }
            return List.copyOf(result);
        } catch (IOException ex) {
            throw new IllegalStateException("Không thể nạp bộ font TTF cho PDF renderer", ex);
        }
    }

    private record FontAsset(String family, String classpath) {}

    private record ResolvedFont(String family, Path filePath) {}
}
