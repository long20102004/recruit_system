package recruit.demo.extraction.section;

import recruit.demo.extraction.pdf.TextBlock;

import java.util.List;

/** Nội dung của một section: các block thuộc về nó theo thứ tự đọc. */
public record SectionContent(CvSection section, List<TextBlock> blocks) {

    /** Toàn bộ text của section, giữ xuống dòng gốc. */
    public String text() {
        StringBuilder sb = new StringBuilder();
        for (TextBlock b : blocks) {
            if (!sb.isEmpty()) {
                sb.append("\n\n");
            }
            sb.append(b.text());
        }
        return sb.toString();
    }
}
