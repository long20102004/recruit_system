package recruit.demo.extraction.mapping;

import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.fields.ContactExtractor;
import recruit.demo.extraction.fields.EducationExtractor;
import recruit.demo.extraction.fields.ExperienceExtractor;
import recruit.demo.extraction.fields.ProjectExtractor;
import recruit.demo.extraction.fields.SkillDictionaryMatcher;
import recruit.demo.extraction.section.CvSection;
import recruit.demo.extraction.section.SectionContent;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Map kết quả các extractor về schema CandidateProfile chuẩn (Giai đoạn 5).
 *
 * <p>Quy ước thiếu dữ liệu: scalar → {@code null}, mảng → rỗng (không bao giờ
 * null để phía gọi không phải null-check). Không trộn "null", "" và [].
 */
public class CvJsonMapper {

    private final SkillDictionaryMatcher skills = new SkillDictionaryMatcher();
    private final ExperienceExtractor experienceExtractor = new ExperienceExtractor(skills);
    private final ProjectExtractor projectExtractor = new ProjectExtractor(skills);

    public CandidateProfile map(Map<CvSection, SectionContent> sections) {
        return map(sections, Map.of());
    }

    public CandidateProfile map(Map<CvSection, SectionContent> sections,
                                Map<CvSection, String> openingHeadings) {
        CandidateProfile out = new CandidateProfile();

        out.setPersonal_info(ContactExtractor.extract(sections.get(CvSection.HEADER)));
        out.setObjective(joinObjective(sections.get(CvSection.OBJECTIVE)));
        out.setEducation(EducationExtractor.extract(sections.get(CvSection.EDUCATION)));
        out.setExperience(experienceExtractor.extract(sections.get(CvSection.EXPERIENCE)));
        out.setPersonal_projects(projectExtractor.extract(sections.get(CvSection.PROJECTS)));
        out.setSkills(splitItems(sections.get(CvSection.SKILLS)));
        out.setCertificates(splitItems(sections.get(CvSection.CERTIFICATES)));
        out.setHonours(splitItems(sections.get(CvSection.HONOURS)));
        out.setLanguages(parseLanguages(sections.get(CvSection.LANGUAGES),
                openingHeadings.get(CvSection.LANGUAGES)));
        return out;
    }

    /** Ghép các dòng mục tiêu bị ngắt thành đoạn hoàn chỉnh. */
    static String joinObjective(SectionContent objective) {
        if (objective == null) {
            return null;
        }
        String joined = objective.text().replace("\n", " ").replaceAll("\\s+", " ").strip();
        return joined.isEmpty() ? null : joined;
    }

    /** Tách mục skills/certificates/honours theo dòng và dấu phân cách, khử trùng giữ thứ tự. */
    static List<String> splitItems(SectionContent section) {
        List<String> out = new ArrayList<>();
        if (section == null) {
            return out;
        }
        Set<String> seen = new LinkedHashSet<>();
        for (String rawLine : section.text().split("\n")) {
            String line = rawLine.replaceAll("^[-•◦]\\s*", "").strip();
            if (line.isEmpty()) {
                continue;
            }
            for (String part : line.split("[,;]")) {
                String item = part.strip();
                if (!item.isEmpty() && seen.add(item.toLowerCase())) {
                    out.add(item);
                }
            }
        }
        return out;
    }

    /** Dòng "Ngôn ngữ: ghi chú" → Language; không có dấu hai chấm thì note = null. */
    static List<CandidateProfile.Language> parseLanguages(SectionContent languages) {
        return parseLanguages(languages, null);
    }

    /**
     * Như trên, kèm tiêu đề mở section để suy tên ngôn ngữ khi các dòng nội dung
     * chỉ còn ghi chú trình độ (ví dụ tiêu đề "NGOẠI NGỮ TIẾNG ANH" + dòng
     * "Nghe 4/10 – ..."). Tên lấy nguyên văn từ tiêu đề, không tự dịch.
     */
    static List<CandidateProfile.Language> parseLanguages(SectionContent languages,
                                                           String openingHeading) {
        List<CandidateProfile.Language> out = new ArrayList<>();
        String fallbackName = languageNameFromHeading(openingHeading);
        if (languages == null) {
            return out;
        }
        List<String> notes = new ArrayList<>();
        for (String rawLine : languages.text().split("\n")) {
            String line = rawLine.replaceAll("^[-•◦✓✔]\\s*", "").strip();
            if (line.isEmpty()) {
                continue;
            }
            CandidateProfile.Language lang = new CandidateProfile.Language();
            int idx = line.indexOf(':');
            if (idx > 0) {
                lang.setLanguage(line.substring(0, idx).strip());
                String note = line.substring(idx + 1).strip();
                lang.setNote(note.isEmpty() ? null : note);
            } else if (looksLikeProfiencyNote(line) && fallbackName != null) {
                lang.setLanguage(fallbackName);
                lang.setNote(line);
            } else {
                lang.setLanguage(line);
            }
            if (lang.getLanguage() != null && !lang.getLanguage().isEmpty()) {
                out.add(lang);
            } else if (lang.getNote() != null) {
                notes.add(lang.getNote());
            }
        }
        if (out.isEmpty() && fallbackName != null && !notes.isEmpty()) {
            CandidateProfile.Language lang = new CandidateProfile.Language();
            lang.setLanguage(fallbackName);
            lang.setNote(String.join(" ", notes));
            out.add(lang);
        }
        return out;
    }

    private static boolean looksLikeProfiencyNote(String line) {
        return line.matches(".*\\d.*")
                || line.length() > 40
                || line.contains("/") && line.length() > 12;
    }

    /** Bóc tên ngôn ngữ khỏi tiêu đề: bỏ các từ chung, giữ nguyên văn phần còn lại. */
    static String languageNameFromHeading(String heading) {
        if (heading == null) {
            return null;
        }
        String name = heading
                .replaceAll("(?iu)\\b(ngoại ngữ|ngôn ngữ|trình độ ngoại ngữ|languages?|foreign languages?|language skills?)\\b", "")
                .replaceAll("[:\\s]+", " ").strip();
        return name.isEmpty() ? null : name;
    }
}
