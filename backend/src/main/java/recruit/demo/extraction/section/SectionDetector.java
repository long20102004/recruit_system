package recruit.demo.extraction.section;

import recruit.demo.extraction.pdf.TextBlock;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Gán block vào section dựa trên tiêu đề (Giai đoạn 2).
 *
 * <p>Một block mở section mới khi dòng đầu của nó khớp từ điển. Các block trước
 * tiêu đề đầu tiên thuộc HEADER. Tiêu đề không rõ (dòng ngắn in hoa toàn bộ,
 * không khớp từ điển) được log để bổ sung từ điển, KHÔNG ép gán section.
 */
public class SectionDetector {

    private static final Logger log = LoggerFactory.getLogger(SectionDetector.class);

    public record DetectionResult(
            List<SectionContent> sections,
            List<String> unknownHeadings,
            Map<CvSection, String> openingHeadings) {
    }

    public DetectionResult detect(List<TextBlock> blocks) {
        blocks = splitBlocksByHeadings(blocks);
        Map<CvSection, List<TextBlock>> grouped = new EnumMap<>(CvSection.class);
        Map<CvSection, String> openingHeadings = new EnumMap<>(CvSection.class);
        List<String> unknownHeadings = new ArrayList<>();
        CvSection current = CvSection.HEADER;

        for (TextBlock block : blocks) {
            String firstLine = firstLine(block.text());
            Optional<CvSection> hit = SectionDictionary.lookup(firstLine);
            if (hit.isPresent()) {
                current = hit.get();
                openingHeadings.putIfAbsent(current, firstLine);
                String rest = restOfBlock(block.text());
                if (!rest.isBlank()) {
                    grouped.computeIfAbsent(current, k -> new ArrayList<>())
                            .add(withText(block, rest));
                }
                continue;
            }
            if (looksLikeHeading(firstLine)) {
                unknownHeadings.add(firstLine.length() > 60
                        ? firstLine.substring(0, 60)
                        : firstLine);
                log.debug("Tiêu đề chưa xác định: {}", firstLine);
            }
            grouped.computeIfAbsent(current, k -> new ArrayList<>()).add(block);
        }

        List<SectionContent> sections = new ArrayList<>();
        for (Map.Entry<CvSection, List<TextBlock>> e : grouped.entrySet()) {
            sections.add(new SectionContent(e.getKey(), List.copyOf(e.getValue())));
        }
        sections.sort((a, b) -> Integer.compare(
                firstOrder(a.blocks()), firstOrder(b.blocks())));
        return new DetectionResult(sections, unknownHeadings, openingHeadings);
    }

    private List<TextBlock> splitBlocksByHeadings(List<TextBlock> blocks) {
        List<TextBlock> out = new ArrayList<>();
        for (TextBlock block : blocks) {
            String text = block.text();
            String[] lines = text.split("\n");
            StringBuilder cur = new StringBuilder();
            for (String line : lines) {
                if (!cur.isEmpty() && SectionDictionary.lookup(line).isPresent()) {
                    out.add(withText(block, cur.toString().strip()));
                    cur.setLength(0);
                }
                cur.append(line).append("\n");
            }
            if (!cur.isEmpty()) {
                out.add(withText(block, cur.toString().strip()));
            }
        }
        return out;
    }

    private static int firstOrder(List<TextBlock> blocks) {
        return blocks.isEmpty() ? Integer.MAX_VALUE : blocks.get(0).order();
    }

    private static String firstLine(String text) {
        int nl = text.indexOf('\n');
        return (nl < 0 ? text : text.substring(0, nl)).strip();
    }

    private static String restOfBlock(String text) {
        int nl = text.indexOf('\n');
        return nl < 0 ? "" : text.substring(nl + 1).strip();
    }

    private static TextBlock withText(TextBlock b, String text) {
        return new TextBlock(b.page(), b.order(), b.x0(), b.y0(), b.x1(), b.y1(),
                b.fontSize(), text);
    }

    /** Heuristic dự phòng: dòng ngắn, chủ yếu in hoa, không phải câu dài. */
    static boolean looksLikeHeading(String line) {
        String s = line.strip();
        if (s.length() < 3 || s.length() > 48) {
            return false;
        }
        if (s.contains("@") || s.contains("://") || s.matches(".*\\d{3,}.*")) {
            return false;
        }
        long upper = s.chars().filter(Character::isUpperCase).count();
        long letters = s.chars().filter(Character::isLetter).count();
        return letters >= 3 && upper >= letters * 0.6;
    }
}
