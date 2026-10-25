package recruit.demo.extraction.pdf;

import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Trích xuất text kèm tọa độ từ PDF (Giai đoạn 1).
 *
 * <p>Không dùng {@code setSortByPosition(true)} một cách mù quáng: tự gom ký tự
 * thành dòng theo tọa độ Y, gom dòng thành block theo khoảng cách dọc, phát hiện
 * cột dựa trên khoảng trắng dọc, rồi mới sắp thứ tự đọc. Mỗi block giữ số trang
 * và bbox để truy vết giá trị trích xuất về nguồn.
 *
 * <p>Thứ tự đọc: các dòng header (15% trên cùng của trang) trước, sau đó từng cột
 * từ trái sang phải, trong mỗi cột sắp theo Y tăng dần (trên xuống dưới).
 */
public class PdfTextExtractor {

    /** CV dài quá ngưỡng này bị từ chối để tránh tài liệu bất thường nghẽn service. */
    public static final int MAX_PAGES = 10;

    /** Ngưỡng text tối thiểu để coi là "có text layer đọc được". */
    public static final int MIN_TEXT_CHARS = 50;

    private static final class Glyph {
        final float x;
        final float y;
        final float h;
        final String ch;

        Glyph(float x, float y, float h, String ch) {
            this.x = x;
            this.y = y;
            this.h = h;
            this.ch = ch;
        }
    }

    private static final class RawLine {
        float y;
        float h;
        float x0 = Float.MAX_VALUE;
        float x1 = Float.MIN_VALUE;
        final List<Glyph> glyphs = new ArrayList<>();

        String text() {
            glyphs.sort(Comparator.comparingDouble(g -> g.x));
            // Ngưỡng ngắt từ theo median advance của CHÍNH dòng này:
            // font giãn chữ (letter-spacing lớn) không bị vỡ từ, PDF không có
            // space tường minh vẫn tách được từ (gap từ lớn hơn hẳn advance).
            List<Float> advances = new ArrayList<>();
            for (int i = 1; i < glyphs.size(); i++) {
                advances.add(glyphs.get(i).x - glyphs.get(i - 1).x);
            }
            advances.sort(Float::compare);
            float medianAdv = advances.isEmpty() ? 5f
                    : advances.get(advances.size() / 2);
            float threshold = Math.max(2f, medianAdv * 1.5f);
            StringBuilder sb = new StringBuilder();
            boolean pendingSpace = false;
            float lastEnd = -1;
            for (Glyph g : glyphs) {
                if (g.ch.isBlank()) {
                    pendingSpace = true;
                    continue;
                }
                if (pendingSpace) {
                    if (!sb.isEmpty()) {
                        sb.append(' ');
                    }
                    pendingSpace = false;
                } else if (lastEnd >= 0 && g.x - lastEnd > threshold) {
                    sb.append(' ');
                }
                sb.append(g.ch);
                lastEnd = g.x + Math.max(1f, g.h * 0.5f);
            }
            return sb.toString().replaceAll("\\s+", " ").strip();
        }
    }

    /** Stripper gom glyph theo tọa độ, không phụ thuộc thứ tự content stream. */
    private static final class PositionStripper extends PDFTextStripper {
        final List<Glyph> glyphs = new ArrayList<>();

        PositionStripper() throws IOException {
            super();
        }

        @Override
        protected void processTextPosition(TextPosition text) {
            String u = text.getUnicode();
            if (u == null || u.isEmpty()) {
                return;
            }
            glyphs.add(new Glyph(text.getX(), text.getY(),
                    Math.max(1f, text.getHeight()), u));
        }
    }

    public record ExtractionResult(List<TextBlock> blocks, String fullText, int pages) {
    }

    public ExtractionResult extract(byte[] pdfBytes) throws IOException {
        try (PDDocument document = Loader.loadPDF(pdfBytes)) {
            int pages = document.getNumberOfPages();
            if (pages > MAX_PAGES) {
                throw new IllegalArgumentException(
                        "File PDF vượt quá " + MAX_PAGES + " trang (nhận " + pages + " trang)");
            }
            List<TextBlock> all = new ArrayList<>();
            StringBuilder full = new StringBuilder();
            for (int p = 1; p <= pages; p++) {
                float pageWidth = document.getPage(p - 1).getMediaBox().getWidth();
                float pageHeight = document.getPage(p - 1).getMediaBox().getHeight();
                PositionStripper stripper = new PositionStripper();
                stripper.setStartPage(p);
                stripper.setEndPage(p);
                stripper.getText(document);
                List<TextBlock> pageBlocks = layoutPage(p, stripper.glyphs, pageWidth, pageHeight,
                        all.size());
                for (TextBlock b : pageBlocks) {
                    all.add(b);
                    full.append(b.text()).append("\n\n");
                }
            }
            return new ExtractionResult(List.copyOf(all), full.toString().strip(), pages);
        }
    }

    private List<TextBlock> layoutPage(int page, List<Glyph> glyphs,
                                       float pageWidth, float pageHeight, int orderBase) {
        List<RawLine> lines = groupLines(glyphs);
        if (lines.isEmpty()) {
            return List.of();
        }
        // Header zone: 15% trên cùng, giữ thứ tự Y.
        float headerLimit = pageHeight * 0.15f;
        List<RawLine> header = new ArrayList<>();
        List<RawLine> body = new ArrayList<>();
        for (RawLine l : lines) {
            (l.y < headerLimit ? header : body).add(l);
        }
        List<RawLine> ordered = new ArrayList<>(header);
        ordered.addAll(splitColumns(body, pageWidth));

        // Gom dòng thành block theo khoảng cách dọc.
        List<TextBlock> blocks = new ArrayList<>();
        List<RawLine> cur = new ArrayList<>();
        RawLine prev = null;
        int order = orderBase;
        for (RawLine l : ordered) {
            if (prev != null && !cur.isEmpty()
                    && (l.y - prev.y) > prev.h * 1.6f + 2f) {
                blocks.add(toBlock(page, order++, cur));
                cur = new ArrayList<>();
            }
            cur.add(l);
            prev = l;
        }
        if (!cur.isEmpty()) {
            blocks.add(toBlock(page, order, cur));
        }
        return blocks;
    }

    private List<RawLine> groupLines(List<Glyph> glyphs) {
        // Gom theo Y trước (bất kể X), rồi tách mỗi nhóm tại khe X lớn
        // (khe cột, không phải khoảng trắng giữa từ).
        List<RawLine> yGroups = new ArrayList<>();
        for (Glyph g : glyphs) {
            RawLine best = null;
            float bestDy = Float.MAX_VALUE;
            for (RawLine l : yGroups) {
                float tol = Math.max(g.h, l.h) * 0.6f;
                float dy = Math.abs(g.y - l.y);
                if (dy <= tol && dy < bestDy) {
                    best = l;
                    bestDy = dy;
                }
            }
            if (best == null) {
                best = new RawLine();
                best.y = g.y;
                best.h = g.h;
                yGroups.add(best);
            }
            best.glyphs.add(g);
            best.h = Math.max(best.h, g.h);
        }
        List<RawLine> lines = new ArrayList<>();
        for (RawLine grp : yGroups) {
            lines.addAll(splitByXGap(grp));
        }
        for (RawLine l : lines) {
            l.x0 = Float.MAX_VALUE;
            l.x1 = Float.MIN_VALUE;
            for (Glyph g : l.glyphs) {
                l.x0 = Math.min(l.x0, g.x);
                l.x1 = Math.max(l.x1, g.x + g.h * 0.5f);
            }
        }
        lines.removeIf(l -> l.text().isEmpty());
        lines.sort(Comparator.comparingDouble(l -> l.y));
        return lines;
    }

    /** Tách một nhóm Y thành nhiều dòng tại khe X vượt trội (khe cột). */
    private List<RawLine> splitByXGap(RawLine grp) {
        List<Glyph> sorted = new ArrayList<>(grp.glyphs);
        sorted.sort(Comparator.comparingDouble(g -> g.x));
        List<Float> gaps = new ArrayList<>();
        for (int i = 1; i < sorted.size(); i++) {
            if (!sorted.get(i).ch.isBlank() && !sorted.get(i - 1).ch.isBlank()) {
                gaps.add(sorted.get(i).x - sorted.get(i - 1).x);
            }
        }
        gaps.sort(Float::compare);
        float median = gaps.isEmpty() ? 5f : gaps.get(gaps.size() / 2);
        float cutAt = Math.max(30f, median * 3f);
        List<RawLine> out = new ArrayList<>();
        RawLine cur = new RawLine();
        cur.y = grp.y;
        cur.h = grp.h;
        Glyph prev = null;
        for (Glyph g : sorted) {
            if (prev != null && !g.ch.isBlank() && !prev.ch.isBlank()
                    && (g.x - prev.x) > cutAt && !cur.glyphs.isEmpty()) {
                out.add(cur);
                cur = new RawLine();
                cur.y = grp.y;
                cur.h = grp.h;
            }
            cur.glyphs.add(g);
            if (!g.ch.isBlank()) {
                prev = g;
            }
        }
        if (!cur.glyphs.isEmpty()) {
            out.add(cur);
        }
        return out;
    }

    /**
     * Phân cột chịu được dòng full-width: tách riêng dòng rộng hơn 60% trang,
     * các dòng còn lại gom 2 cụm theo tâm X tại khe lớn nhất. Dòng full-width
     * giữ nguyên vị trí Y tương đối; hai cột phát theo thứ tự trái → phải.
     */
    private List<RawLine> splitColumns(List<RawLine> body, float pageWidth) {
        if (body.size() < 4) {
            return body;
        }
        List<RawLine> full = new ArrayList<>();
        List<RawLine> narrow = new ArrayList<>();
        for (RawLine l : body) {
            ((l.x1 - l.x0) > pageWidth * 0.60f ? full : narrow).add(l);
        }
        if (narrow.size() < 4) {
            return body;
        }
        List<RawLine> byCenter = new ArrayList<>(narrow);
        byCenter.sort(Comparator.comparingDouble(l -> (l.x0 + l.x1) / 2f));
        float bestGap = 0;
        int bestIdx = -1;
        for (int i = 1; i < byCenter.size(); i++) {
            float gap = center(byCenter.get(i)) - center(byCenter.get(i - 1));
            if (gap > bestGap) {
                bestGap = gap;
                bestIdx = i;
            }
        }
        // Khe phải đủ lớn và hai bên đều có tối thiểu 2 dòng chồng lấn dọc.
        if (bestIdx < 0 || bestGap < pageWidth * 0.08f) {
            return body;
        }
        List<RawLine> left = new ArrayList<>(byCenter.subList(0, bestIdx));
        List<RawLine> right = new ArrayList<>(byCenter.subList(bestIdx, byCenter.size()));
        if (left.size() < 2 || right.size() < 2 || !overlapVertically(left, right)) {
            return body;
        }
        
        // Chống nhận diện sai CV 1 cột có ngày tháng căn lề phải (splitByXGap tạo ra các mảnh cùng Y).
        // Nếu nhiều mảnh có cùng Y, đây là cấu trúc bảng hoặc dòng được căn lề 2 bên -> đọc theo dòng.
        int sameYCount = 0;
        for (RawLine l : left) {
            for (RawLine r : right) {
                if (Math.abs(l.y - r.y) < Math.max(l.h, r.h) * 0.5f) {
                    sameYCount++;
                    break;
                }
            }
        }
        if (sameYCount > Math.max(1, Math.min(left.size(), right.size()) * 0.3f)) {
            return body;
        }

        List<RawLine> ordered = new ArrayList<>(full.size() + left.size() + right.size());
        List<RawLine> leftByY = byY(left);
        List<RawLine> rightByY = byY(right);
        List<RawLine> fullByY = byY(full);
        // Đơn giản và an toàn cho section detection: full-width theo Y,
        // sau đó toàn bộ cột trái, rồi cột phải (không trộn kẽ dòng hai cột).
        ordered.addAll(fullByY);
        ordered.addAll(leftByY);
        ordered.addAll(rightByY);
        return ordered;
    }

    private static float center(RawLine l) {
        return (l.x0 + l.x1) / 2f;
    }

    private static List<RawLine> byY(List<RawLine> lines) {
        List<RawLine> out = new ArrayList<>(lines);
        out.sort(Comparator.comparingDouble(l -> l.y));
        return out;
    }

    private static boolean overlapVertically(List<RawLine> a, List<RawLine> b) {
        float a0 = Float.MAX_VALUE;
        float a1 = Float.MIN_VALUE;
        float b0 = Float.MAX_VALUE;
        float b1 = Float.MIN_VALUE;
        for (RawLine l : a) {
            a0 = Math.min(a0, l.y);
            a1 = Math.max(a1, l.y);
        }
        for (RawLine l : b) {
            b0 = Math.min(b0, l.y);
            b1 = Math.max(b1, l.y);
        }
        float overlap = Math.min(a1, b1) - Math.max(a0, b0);
        float span = Math.max(a1, b1) - Math.min(a0, b0);
        return span > 0 && overlap / span > 0.25f;
    }

    private TextBlock toBlock(int page, int order, List<RawLine> lines) {
        StringBuilder sb = new StringBuilder();
        float x0 = Float.MAX_VALUE;
        float y0 = Float.MAX_VALUE;
        float x1 = Float.MIN_VALUE;
        float y1 = Float.MIN_VALUE;
        float fs = 0;
        for (int i = 0; i < lines.size(); i++) {
            if (i > 0) {
                sb.append('\n');
            }
            sb.append(lines.get(i).text());
            RawLine l = lines.get(i);
            x0 = Math.min(x0, l.x0);
            y0 = Math.min(y0, l.y - l.h);
            x1 = Math.max(x1, l.x1);
            y1 = Math.max(y1, l.y);
            fs += l.h;
        }
        return new TextBlock(page, order, x0, y0, x1, y1,
                fs / lines.size(), TextNormalizer.normalize(sb.toString()));
    }
}
