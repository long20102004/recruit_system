package recruit.demo.extraction.fields;

import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.section.SectionContent;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * State machine tách các công việc trong section kinh nghiệm (Giai đoạn 4).
 *
 * <p>Một dòng chứa khoảng thời gian (MM/YYYY–MM/YYYY, YYYY–YYYY) mở một bản ghi
 * công việc mới; mọi dòng sau (mô tả, marker "Công nghệ sử dụng",
 * "Dự án đã thực hiện", "+", "•") thuộc về bản ghi đang mở cho tới header mới.
 * Công nghệ chỉ lấy trong phạm vi chunk của từng công việc — không bao giờ sao
 * chép toàn bộ mục kỹ năng chung.
 */
public class ExperienceExtractor {

    private static final Pattern COMPANY_HINT = Pattern.compile(
            "(?iu).*(công ty|corporation|corp\\b|inc\\b|ltd|jsc|company|group|studio|lab|bank|tnhh|cp\\b).*");

    private static final Pattern TITLE_HINT = Pattern.compile(
            "(?iu).*(thực tập|intern|developer|lập trình|kỹ sư|engineer|analyst|tester|designer|manager|chuyên viên|nhân viên|fresher|junior|senior|lead).*");

    private final SkillDictionaryMatcher skills;

    public ExperienceExtractor(SkillDictionaryMatcher skills) {
        this.skills = skills;
    }

    public List<CandidateProfile.Experience> extract(SectionContent experience) {
        List<CandidateProfile.Experience> out = new ArrayList<>();
        if (experience == null) {
            return out;
        }
        // Chia chunk: dòng có khoảng thời gian mở job mới.
        List<List<String>> chunks = new ArrayList<>();
        List<String> current = new ArrayList<>();
        for (String rawLine : experience.text().split("\n")) {
            String line = rawLine.strip();
            if (line.isEmpty()) {
                continue;
            }
            if (isJobHeader(line) && !current.isEmpty()) {
                chunks.add(current);
                current = new ArrayList<>();
            }
            current.add(line);
        }
        if (!current.isEmpty()) {
            chunks.add(current);
        }
        for (List<String> chunk : chunks) {
            out.add(parseJob(chunk));
        }
        return out;
    }

    private boolean isJobHeader(String line) {
        return RegexFieldExtractor.DATE_RANGE.matcher(line).find()
                || RegexFieldExtractor.YEAR_RANGE.matcher(line).find()
                || RegexFieldExtractor.MONTH_WORD_YEAR_RANGE.matcher(line).find();
    }

    /** Bỏ ngoặc thời gian (kể cả ngoặc thiếu đóng) và ngày thừa cuối đoạn header. */
    private static String cleanHeaderPart(String part) {
        String p = part.replaceAll("\\([^)]*\\)?", "").strip();
        p = p.replaceAll("\\b\\d{1,2}[/-]\\d{4}\\s*$", "").strip();
        p = p.replaceAll("\\s+[–—\\-|]+\\s*$", "").strip();
        return p;
    }

    private CandidateProfile.Experience parseJob(List<String> chunk) {
        CandidateProfile.Experience job = new CandidateProfile.Experience();
        job.setDescription(new ArrayList<>());
        String joined = String.join("\n", chunk);

        // Thời gian: khoảng đầu tiên trong chunk.
        Matcher range = RegexFieldExtractor.DATE_RANGE.matcher(joined);
        Matcher yearRange = RegexFieldExtractor.YEAR_RANGE.matcher(joined);
        Matcher monthWordRange = RegexFieldExtractor.MONTH_WORD_YEAR_RANGE.matcher(joined);
        if (range.find()) {
            job.setStart_date(range.group(1));
            job.setEnd_date(range.group(2));
        } else if (yearRange.find()) {
            job.setStart_date(yearRange.group(1));
            job.setEnd_date(yearRange.group(2));
        } else if (monthWordRange.find()) {
            job.setStart_date(monthWordRange.group(1));
            job.setEnd_date(monthWordRange.group(2));
        }

        // Công ty và chức danh: ưu tiên dòng header (dòng đầu chứa thời gian).
        String headerLine = chunk.get(0);
        String[] parts = headerLine.split("\\s+[–—\\-|]\\s*|\\s*\\|\\s*");
        String company = null;
        String title = null;
        for (String part : parts) {
            String p = cleanHeaderPart(part);
            if (p.isEmpty()
                    || RegexFieldExtractor.DATE_RANGE.matcher(p).find()
                    || RegexFieldExtractor.YEAR_RANGE.matcher(p).find()
                    || RegexFieldExtractor.MONTH_WORD_YEAR_RANGE.matcher(p).find()) {
                continue;
            }
            if (company == null && COMPANY_HINT.matcher(p).find()) {
                company = p;
            } else if (title == null && TITLE_HINT.matcher(p).find()) {
                title = p;
            }
        }
        if (company == null) {
            for (String part : parts) {
                String p = cleanHeaderPart(part);
                if (!p.isEmpty()
                        && !RegexFieldExtractor.DATE_RANGE.matcher(p).find()
                        && !RegexFieldExtractor.YEAR_RANGE.matcher(p).find()
                        && !RegexFieldExtractor.MONTH_WORD_YEAR_RANGE.matcher(p).find()) {
                    company = p;
                    break;
                }
            }
        }
        job.setCompany(company);
        job.setJob_title(title);

        // Mô tả: mọi dòng còn lại, bóc marker nhưng giữ nguyên nội dung.
        for (int i = 1; i < chunk.size(); i++) {
            String desc = chunk.get(i)
                    .replaceAll("(?iu)^[-•◦\\s]*(dự án đã thực hiện|công nghệ sử dụng)\\s*[:\\-]?\\s*", "")
                    .strip();
            if (!desc.isEmpty()) {
                job.getDescription().add(desc);
            }
        }
        return job;
    }
}
