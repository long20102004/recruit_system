package recruit.demo.extraction.pdf;

/**
 * Chuẩn hóa text nhưng GIỮ ý nghĩa: không xóa dấu câu, số liệu, URL.
 * - \r, tab, non-breaking space -> khoảng trắng thường
 * - Nối từ bị ngắt dòng bằng gạch nối: "lập-\ntrình" -> "lập trình"
 *   (giữ nguyên dấu gạch nối đứng giữa từ không bị ngắt dòng)
 * - Chuẩn hóa bullet đầu dòng về "- "
 * - Gộp dòng trống thừa (tối đa 1 dòng trống liên tiếp)
 */
public final class TextNormalizer {

    private TextNormalizer() {
    }

    public static String normalize(String raw) {
        if (raw == null) {
            return "";
        }
        String s = raw.replace("\r\n", "\n").replace('\r', '\n');
        s = s.replace('\u00A0', ' ').replace('\t', ' ');
        // Nối từ bị ngắt dòng: chữ + gạch nối + xuống dòng + chữ
        s = s.replaceAll("(\\p{L})-\\n(\\p{L})", "$1$2");
        String[] lines = s.split("\n", -1);
        StringBuilder out = new StringBuilder(s.length());
        boolean prevBlank = false;
        for (String line : lines) {
            // Chuẩn hóa bullet đầu dòng, giữ nội dung sau bullet
            String t = line.replaceAll("^[ \\t]*[•◦▪▫○●\\-\\*+]\\s+", "- ");
            t = t.replaceAll("[ \\t]{2,}", " ").strip();
            boolean blank = t.isEmpty();
            if (blank && prevBlank) {
                continue;
            }
            prevBlank = blank;
            out.append(t).append('\n');
        }
        return out.toString().strip();
    }
}
