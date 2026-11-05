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
 * <p>Dùng PDFBox ghép từ với {@code setSortByPosition(true)}, gom các run
 * thành dòng theo tọa độ Y, phát hiện cột dựa trên khoảng trắng dọc,
 * rồi mới sắp thứ tự đọc. Mỗi block giữ số trang
 * và bbox để truy vết giá trị trích xuất về nguồn.
 *
 * <p>Recursive XY-cut khôi phục thứ tự trên → dưới, trái → phải, không giả định
 * vị trí header hay số cột. Các mảnh ngày tháng hẹp vẫn được đọc cùng dòng.
 */
public class PdfTextExtractor {

    /** CV dài quá ngưỡng này bị từ chối để tránh tài liệu bất thường nghẽn service. */
    public static final int MAX_PAGES = 10;

    /** Ngưỡng text tối thiểu để coi là "có text layer đọc được". */
    public static final int MIN_TEXT_CHARS = 50;

    private static final class Run {
        final float x;
        final float y;
        final float h;
        final float w;
        final float spaceWidth;
        final String text;

        Run(float x, float y, float h, float w, float spaceWidth, String text) {
            this.x = x;
            this.y = y;
            this.h = h;
            this.w = w;
            this.spaceWidth = spaceWidth;
            this.text = text;
        }
    }

    private static final class RawLine {
        float y;
        float h;
        float x0 = Float.MAX_VALUE;
        float x1 = Float.MIN_VALUE;
        final List<Run> runs = new ArrayList<>();

        String text() {
            runs.sort(Comparator.comparingDouble(r -> r.x));
            StringBuilder sb = new StringBuilder();
            for (Run run : runs) {
                if (!sb.isEmpty()) sb.append(' ');
                sb.append(run.text);
            }
            return sb.toString();
        }
    }

    /** PDFBox owns word boundaries; geometry is used only for layout. */
    private static final class PositionStripper extends PDFTextStripper {
        final List<Run> runs = new ArrayList<>();

        PositionStripper() throws IOException {
            super();
            setSortByPosition(true);
        }

        @Override
        protected void writeString(String text, List<TextPosition> positions) {
            if (text.isBlank() || positions.isEmpty()) return;
            // PDFBox (sortByPosition) can hand one "word" made of glyphs from two columns
            // that share a baseline ("GPA: 7.8 ... 03/2025 IT Engineer"). Split such a run
            // wherever two consecutive glyphs are far apart, so XY-cut can see the gutter.
            boolean aligned = text.length() == positions.size();
            int start = 0;
            for (int i = 1; i <= positions.size(); i++) {
                boolean cut = i == positions.size();
                if (!cut) {
                    TextPosition a = positions.get(i - 1);
                    TextPosition b = positions.get(i);
                    float gap = b.getXDirAdj() - (a.getXDirAdj() + a.getWidthDirAdj());
                    float h = Math.max(1f, Math.max(a.getHeightDir(), b.getHeightDir()));
                    float sp = Float.isFinite(a.getWidthOfSpace()) && a.getWidthOfSpace() > 0 ? a.getWidthOfSpace() : h * 0.5f;
                    cut = gap > Math.max(1.2f * h, 3f * sp) || Math.abs(b.getYDirAdj() - a.getYDirAdj()) > h;
                }
                if (cut) {
                    List<TextPosition> part = positions.subList(start, i);
                    String partText = aligned ? text.substring(start, i) : unicode(part);
                    if (!partText.isBlank()) addRun(partText.strip(), part);
                    start = i;
                }
            }
        }

        private static String unicode(List<TextPosition> part) {
            StringBuilder sb = new StringBuilder();
            TextPosition prev = null;
            for (TextPosition p : part) {
                if (prev != null) {
                    float gap = p.getXDirAdj() - (prev.getXDirAdj() + prev.getWidthDirAdj());
                    float sp = Float.isFinite(prev.getWidthOfSpace()) && prev.getWidthOfSpace() > 0
                            ? prev.getWidthOfSpace() : prev.getHeightDir() * 0.5f;
                    if (gap > 0.5f * sp && !sb.isEmpty() && sb.charAt(sb.length() - 1) != ' ') sb.append(' ');
                }
                if (p.getUnicode() != null) sb.append(p.getUnicode());
                prev = p;
            }
            return sb.toString();
        }

        private void addRun(String text, List<TextPosition> positions) {
            TextPosition first = positions.getFirst();
            TextPosition last = positions.getLast();
            float height = 1f;
            List<Float> spaces = new ArrayList<>();
            List<Float> widths = new ArrayList<>();
            for (TextPosition position : positions) {
                height = Math.max(height, position.getHeightDir());
                float space = position.getWidthOfSpace();
                if (Float.isFinite(space) && space > 0) spaces.add(space);
                float width = position.getWidthDirAdj();
                if (Float.isFinite(width) && width > 0) widths.add(width);
            }
            float spaceWidth = !spaces.isEmpty() ? median(spaces)
                    : widths.isEmpty() ? height * 0.5f : median(widths);
            runs.add(new Run(first.getXDirAdj(), first.getYDirAdj(), height,
                    Math.max(0f, last.getXDirAdj() + last.getWidthDirAdj() - first.getXDirAdj()),
                    spaceWidth, text));
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
                PositionStripper stripper = new PositionStripper();
                stripper.setStartPage(p);
                stripper.setEndPage(p);
                stripper.getText(document);
                List<TextBlock> pageBlocks = layoutPage(p, stripper.runs, all.size());
                for (TextBlock b : pageBlocks) {
                    all.add(b);
                    full.append(b.text()).append("\n\n");
                }
            }
            return new ExtractionResult(List.copyOf(all), full.toString().strip(), pages);
        }
    }

    private List<TextBlock> layoutPage(int page, List<Run> runs, int orderBase) {
        List<RawLine> lines = groupLines(runs);
        if (lines.isEmpty()) {
            return List.of();
        }
        List<TextBlock> blocks = new ArrayList<>();
        xyCut(page, lines, blocks, orderBase);
        return blocks;
    }

    private List<RawLine> groupLines(List<Run> runs) {
        // Gom theo Y trước (bất kể X), rồi tách mỗi nhóm tại khe X lớn
        // (khe cột, không phải khoảng trắng giữa từ).
        List<RawLine> yGroups = new ArrayList<>();
        List<Run> sorted = new ArrayList<>(runs);
        sorted.sort(Comparator.comparingDouble((Run g) -> g.y).thenComparingDouble(g -> g.x));
        for (Run g : sorted) {
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
            best.runs.add(g);
            best.h = Math.max(best.h, g.h);
        }
        List<RawLine> lines = new ArrayList<>();
        for (RawLine grp : yGroups) {
            lines.addAll(splitByXGap(grp));
        }
        for (RawLine l : lines) {
            l.x0 = Float.MAX_VALUE;
            l.x1 = Float.MIN_VALUE;
            for (Run g : l.runs) {
                l.x0 = Math.min(l.x0, g.x);
                l.x1 = Math.max(l.x1, g.x + g.w);
            }
        }
        lines.removeIf(l -> l.text().isEmpty());
        lines.sort(Comparator.comparingDouble(l -> l.y));
        return lines;
    }

    /** Tách một nhóm Y thành nhiều dòng tại khe X vượt trội (khe cột). */
    private List<RawLine> splitByXGap(RawLine grp) {
        List<Run> sorted = new ArrayList<>(grp.runs);
        sorted.sort(Comparator.comparingDouble(g -> g.x));
        List<RawLine> out = new ArrayList<>();
        RawLine cur = new RawLine();
        cur.y = grp.y;
        cur.h = grp.h;
        Run prev = null;
        for (Run g : sorted) {
            float cutAt = Math.max(grp.h * 1.2f,
                    3f * Math.max(g.spaceWidth, prev == null ? g.spaceWidth : prev.spaceWidth));
            if (prev != null && (g.x - prev.x - prev.w) > cutAt && !cur.runs.isEmpty()) {
                out.add(cur);
                cur = new RawLine();
                cur.y = grp.y;
                cur.h = grp.h;
            }
            cur.runs.add(g);
            prev = g;
        }
        if (!cur.runs.isEmpty()) {
            out.add(cur);
        }
        return out;
    }

    private static float median(List<Float> values) {
        List<Float> sorted = new ArrayList<>(values);
        sorted.sort(Float::compare);
        int middle = sorted.size() / 2;
        return sorted.size() % 2 == 0
                ? (sorted.get(middle - 1) + sorted.get(middle)) / 2f : sorted.get(middle);
    }

    /** Cuts are projection gaps: no segment may cross the chosen whitespace. */
    private void xyCut(int page, List<RawLine> region, List<TextBlock> blocks, int orderBase) {
        float glyphHeight = median(region.stream().flatMap(l -> l.runs.stream())
                .map(g -> g.h).toList());
        List<RawLine> byX = new ArrayList<>(region);
        byX.sort(Comparator.comparingDouble(l -> l.x0));
        float regionWidth = (float) region.stream().mapToDouble(l -> l.x1).max().orElseThrow()
                - byX.getFirst().x0;
        float end = byX.getFirst().x1;
        float widest = 0;
        int split = -1;
        for (int i = 1; i < byX.size(); i++) {
            float gap = byX.get(i).x0 - end;
            if (gap >= Math.max(6f, 0.8f * glyphHeight) && gap > widest
                    && realColumn(byX.subList(0, i), regionWidth)
                    && realColumn(byX.subList(i, byX.size()), regionWidth)) {
                widest = gap;
                split = i;
            }
            end = Math.max(end, byX.get(i).x1);
        }
        if (split >= 0) {
            xyCut(page, byX.subList(0, split), blocks, orderBase);
            xyCut(page, byX.subList(split, byX.size()), blocks, orderBase);
            return;
        }

        List<RawLine> byTop = new ArrayList<>(region);
        byTop.sort(Comparator.comparingDouble(l -> l.y - l.h));
        float lineHeight = median(region.stream().map(l -> l.h).toList());
        end = byTop.getFirst().y;
        widest = 0;
        split = -1;
        for (int i = 1; i < byTop.size(); i++) {
            RawLine line = byTop.get(i);
            float gap = line.y - line.h - end;
            if (gap >= 1.5f * lineHeight && gap > widest) {
                widest = gap;
                split = i;
            }
            end = Math.max(end, line.y);
        }
        if (split >= 0) {
            xyCut(page, byTop.subList(0, split), blocks, orderBase);
            xyCut(page, byTop.subList(split, byTop.size()), blocks, orderBase);
            return;
        }

        // A leaf is a block; join narrow date/label segments back into their rows.
        List<RawLine> rows = new ArrayList<>();
        List<RawLine> byY = new ArrayList<>(region);
        byY.sort(Comparator.comparingDouble((RawLine l) -> l.y).thenComparingDouble(l -> l.x0));
        for (RawLine segment : byY) {
            RawLine row = rows.isEmpty() ? null : rows.getLast();
            if (row == null || Math.abs(segment.y - row.y) > Math.max(segment.h, row.h) * 0.6f) {
                row = new RawLine();
                row.y = segment.y;
                row.h = segment.h;
                rows.add(row);
            }
            row.runs.addAll(segment.runs);
            row.h = Math.max(row.h, segment.h);
            row.x0 = Math.min(row.x0, segment.x0);
            row.x1 = Math.max(row.x1, segment.x1);
        }
        blocks.add(toBlock(page, orderBase + blocks.size(), rows));
    }

    /**
     * A side of a vertical gutter is a real text column when it holds >= 3 segments and its
     * horizontal extent covers >= 25 % of the region. The extent (not the median line width)
     * keeps sidebars made of short lines (dates, "GPA: 7.8", certificate names) as columns,
     * while a narrow strip of dates or labels (timeline, right-aligned dates) is not a column.
     */
    private boolean realColumn(List<RawLine> segments, float regionWidth) {
        if (segments.size() < 3) {
            return false;
        }
        float x0 = Float.MAX_VALUE;
        float x1 = -Float.MAX_VALUE;
        for (RawLine l : segments) {
            x0 = Math.min(x0, l.x0);
            x1 = Math.max(x1, l.x1);
        }
        return x1 - x0 >= regionWidth * 0.25f;
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
