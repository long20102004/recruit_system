package recruit.demo.extraction.fields;

import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.section.SectionContent;

import java.util.List;
import java.util.regex.Pattern;

/**
 * Trích xuất thông tin liên hệ từ vùng HEADER (dòng đầu CV).
 *
 * <p>Tên: dòng ngắn đầu tiên có 2–4 từ, không chứa số/@/URL. Đây là heuristic;
 * trường hợp khó (tên lẫn trong dòng khác) thuộc phạm vi NER giai đoạn 6.
 */
public final class ContactExtractor {

    private static final Pattern NAME_LINE =
            Pattern.compile("^[\\p{L}][\\p{L} .'-]{1,48}$");

    private ContactExtractor() {
    }

    public static CandidateProfile.PersonalInfo extract(SectionContent header) {
        CandidateProfile.PersonalInfo info = new CandidateProfile.PersonalInfo();
        if (header == null) {
            return info;
        }
        String text = header.text();
        RegexFieldExtractor.first(RegexFieldExtractor.EMAIL, text).ifPresent(info::setEmail);
        if (info.getEmail() == null) {
            // Dự phòng PDF chèn space quanh @ (wrap email): thử trên bản đã nối.
            String joined = text.replaceAll("\\s*@\\s*", "@");
            RegexFieldExtractor.first(RegexFieldExtractor.EMAIL, joined).ifPresent(info::setEmail);
        }
        RegexFieldExtractor.first(RegexFieldExtractor.VN_PHONE, text).ifPresent(info::setPhone);
        for (String url : RegexFieldExtractor.all(RegexFieldExtractor.URL, text)) {
            String low = url.toLowerCase();
            if (low.contains("github.com") || low.contains("gitlab.com")) {
                if (info.getGithub_url() == null) {
                    info.setGithub_url(url);
                }
            }
        }
        info.setFull_name(guessName(text));
        return info;
    }

    static String guessName(String text) {
        if (text == null) {
            return null;
        }
        for (String rawLine : text.split("\n")) {
            String line = rawLine.strip();
            if (line.isEmpty() || line.length() > 48) {
                continue;
            }
            if (line.contains("@") || line.contains("://") || line.matches(".*\\d.*")) {
                continue;
            }
            String[] words = line.split("\\s+");
            if (words.length < 2 || words.length > 4) {
                continue;
            }
            if (NAME_LINE.matcher(line).matches()) {
                return line;
            }
        }
        return null;
    }
}
