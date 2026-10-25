package recruit.demo.extraction.fields;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Regex cho trường có định dạng cố định (Giai đoạn 3).
 * Mọi matcher đều giữ NGUYÊN chuỗi nguồn (không chuẩn hóa giá trị).
 */
public final class RegexFieldExtractor {

    private RegexFieldExtractor() {
    }

    public static final Pattern EMAIL =
            Pattern.compile("[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}");

    public static final Pattern URL =
            Pattern.compile("(?:https?://|www\\.)[^\\s)>\"]+|(?:github|gitlab|linkedin)\\.com/[^\\s)>\"]+",
                    Pattern.CASE_INSENSITIVE);

    /** SĐT Việt Nam: 0xxxxxxxxx hoặc +84..., cho phép khoảng trắng/chấm phân cách. */
    public static final Pattern VN_PHONE =
            Pattern.compile("(?:\\+84|0)(?:[\\s.]?\\d){9}\\b");

    /** GPA dạng "3.74 / 4.0", "GPA: 8.8", "GPA 3.1". */
    public static final Pattern GPA =
            Pattern.compile("(?i)\\bGPA\\s*[:=]?\\s*(\\d+[.,]\\d+)(?:\\s*/\\s*(\\d+[.,]\\d+))?");

    /** Khoảng thời gian MM/YYYY–MM/YYYY hoặc MM/YYYY–hiện tại. */
    public static final Pattern DATE_RANGE =
            Pattern.compile("(\\d{1,2}[/-]\\d{4})\\s*[–—\\-~]+\\s*(\\d{1,2}[/-]\\d{4}|hiện tại|hien tai|present|now|current)",
                    Pattern.CASE_INSENSITIVE);

    /** Khoảng năm YYYY–YYYY. */
    public static final Pattern YEAR_RANGE =
            Pattern.compile("\\b((?:19|20)\\d{2})\\s*[–—\\-]\\s*((?:19|20)\\d{2}|hiện tại|hien tai|present|now|current)",
                    Pattern.CASE_INSENSITIVE);

    /** Khoảng tháng dạng chữ (October 2025 - May 2026). */
    public static final Pattern MONTH_WORD_YEAR_RANGE =
            Pattern.compile("(?i)([a-z]+\\s+(?:19|20)\\d{2})\\s*[–—\\-~]+\\s*([a-z]+\\s+(?:19|20)\\d{2}|hiện tại|hien tai|present|now|current)");

    /** Năm tốt nghiệp: "Năm tốt nghiệp: 2025", "Tốt nghiệp 2025", "Graduated 2025". */
    public static final Pattern GRADUATION_YEAR =
            Pattern.compile("(?iu)(?:năm tốt nghiệp|tốt nghiệp|graduated|graduation)\\s*:?\\s*((?:19|20)\\d{2})");

    /** Quy mô nhóm: "Số lượng thành viên: 4", "Team size: 4". Chỉ điền khi ghi rõ. */
    public static final Pattern TEAM_SIZE =
            Pattern.compile("(?iu)(?:số lượng thành viên|team size|số thành viên|members?)\\s*[:=]?\\s*(\\d{1,2})\\b");

    /** Năm sinh: "Sinh năm: 2002", "Năm sinh 2002", "Ngày sinh: 29/06/2003". */
    public static final Pattern BIRTH =
            Pattern.compile("(?iu)(?:sinh năm|năm sinh|ngày sinh|born|date of birth)\\s*[:\\-]?\\s*(\\d{1,2}[/.\\-]\\d{1,2}[/.\\-]\\d{2,4}|\\d{4})");

    /** Tháng/năm đơn lẻ. */
    public static final Pattern MONTH_YEAR =
            Pattern.compile("\\b\\d{1,2}[/-]\\d{4}\\b");

    /** Năm đơn lẻ 1900–2099. */
    public static final Pattern YEAR =
            Pattern.compile("\\b((?:19|20)\\d{2})\\b");

    public static Optional<String> first(Pattern pattern, String text) {
        if (text == null) {
            return Optional.empty();
        }
        Matcher m = pattern.matcher(text);
        if (!m.find()) {
            return Optional.empty();
        }
        return Optional.of(stripTrailingPunct(m.group()));
    }

    public static List<String> all(Pattern pattern, String text) {
        List<String> out = new ArrayList<>();
        if (text == null) {
            return out;
        }
        Matcher m = pattern.matcher(text);
        while (m.find()) {
            out.add(stripTrailingPunct(m.group()));
        }
        return out;
    }

    public static Optional<String> firstGroup(Pattern pattern, String text, int group) {
        if (text == null) {
            return Optional.empty();
        }
        Matcher m = pattern.matcher(text);
        if (!m.find()) {
            return Optional.empty();
        }
        return Optional.ofNullable(m.group(group));
    }

    private static String stripTrailingPunct(String s) {
        return s.replaceAll("[.,;:!?)\"']+$", "");
    }
}
