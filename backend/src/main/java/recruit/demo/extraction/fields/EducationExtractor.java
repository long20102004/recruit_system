package recruit.demo.extraction.fields;

import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.section.SectionContent;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Trích xuất học vấn: mỗi dòng trường học mở một bản ghi mới (state machine).
 */
public final class EducationExtractor {

    private static final Pattern SCHOOL_LINE = Pattern.compile(
            "(?iu).*(đại học|university|college|học viện|cao đẳng|institute|polytechnic|trường\\s+\\w+).*");

    private static final Pattern MAJOR_LINE = Pattern.compile(
            "(?iu).*(ngành|major|chuyên ngành|khoa:?\\s|chuyen nganh).*");

    private EducationExtractor() {
    }

    public static List<CandidateProfile.Education> extract(SectionContent education) {
        List<CandidateProfile.Education> out = new ArrayList<>();
        if (education == null) {
            return out;
        }
        CandidateProfile.Education current = null;
        for (String rawLine : education.text().split("\n")) {
            String line = rawLine.strip().replaceAll("^[-•◦]\\s*", "");
            if (line.isEmpty()) {
                continue;
            }
            if (SCHOOL_LINE.matcher(line).matches()) {
                current = new CandidateProfile.Education();
                current.setSchool(stripSchoolPrefix(line));
                out.add(current);
                assignYears(current, line);
                continue;
            }
            if (current == null) {
                continue;
            }
            if (current.getMajor() == null && MAJOR_LINE.matcher(line).find()) {
                current.setMajor(stripLabel(line));
            }
            final CandidateProfile.Education target = current;
            java.util.regex.Matcher gpaMatcher =
                    RegexFieldExtractor.GPA.matcher(line);
            if (gpaMatcher.find() && target.getGpa() == null) {
                String value = gpaMatcher.group(1).replace(',', '.');
                String scale = gpaMatcher.group(2);
                target.setGpa(scale == null ? value : value + " / " + scale.replace(',', '.'));
            }
            assignYears(current, line);
        }
        // Năm tốt nghiệp dạng "Năm tốt nghiệp: 2025" thắng mọi suy đoán khác.
        String full = education.text();
        RegexFieldExtractor.firstGroup(RegexFieldExtractor.GRADUATION_YEAR, full, 1)
                .ifPresent(grad -> {
                    try {
                        int year = Integer.parseInt(grad);
                        if (!out.isEmpty() && out.get(out.size() - 1).getEnd_year() == null) {
                            out.get(out.size() - 1).setEnd_year(year);
                        }
                    } catch (NumberFormatException ignored) {
                    }
                });
        return out;
    }

    private static void assignYears(CandidateProfile.Education current, String line) {
        Matcher range = RegexFieldExtractor.YEAR_RANGE.matcher(line);
        if (range.find()) {
            try {
                if (current.getStart_year() == null) {
                    current.setStart_year(Integer.parseInt(range.group(1)));
                }
                String end = range.group(2);
                if (!end.matches("(?i)hiện tại|hien tai|present|now|current")
                        && current.getEnd_year() == null) {
                    current.setEnd_year(Integer.parseInt(end));
                }
            } catch (NumberFormatException ignored) {
            }
        }
    }

    private static String stripLabel(String line) {
        int idx = line.indexOf(':');
        String s = idx >= 0 ? line.substring(idx + 1) : line;
        return s.strip().replaceAll("^(là|la)\\s+", "");
    }

    /** Bỏ bullet và nhãn "Trường:"/"School:", giữ nguyên tên trường nguồn. */
    private static String stripSchoolPrefix(String line) {
        String s = line.replaceAll("^[⬧•\\-\\*+\\s]+", "").strip();
        s = s.replaceAll("(?iu)^(trường|school)\\s*:\\s*", "");
        return s.strip();
    }
}
