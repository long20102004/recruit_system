package recruit.demo.extraction.validation;

import recruit.demo.dto.CandidateProfile;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Validation + dedup + kiểm tra nhất quán (Giai đoạn 5).
 *
 * <p>Không bao giờ bịa dữ liệu để "hoàn tất" JSON: chỉ sửa lỗi cơ học chắc chắn
 * (trùng lặp y hệt), còn lại ghi cảnh báo để đo lỗi và cải tiến quy tắc.
 */
public class CvValidator {

    private static final Pattern EMAIL_FORMAT =
            Pattern.compile("^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}$");

    private static final Pattern URL_FORMAT =
            Pattern.compile("^(https?://|www\\.|[a-z]+\\.(com|vn|org|net|io|dev|ai)/).+",
                    Pattern.CASE_INSENSITIVE);

    public record ValidationResult(CandidateProfile profile, List<String> warnings) {
    }

    public ValidationResult validate(CandidateProfile profile) {
        List<String> warnings = new ArrayList<>();
        if (profile == null) {
            warnings.add("profile null");
            return new ValidationResult(new CandidateProfile(), warnings);
        }

        checkEmail(profile, warnings);
        checkUrls(profile, warnings);
        checkDates(profile, warnings);
        checkGpa(profile, warnings);
        dedupDescriptions(profile, warnings);
        return new ValidationResult(profile, warnings);
    }

    private void checkEmail(CandidateProfile p, List<String> warnings) {
        String email = p.getPersonal_info() != null ? p.getPersonal_info().getEmail() : null;
        if (email != null && !EMAIL_FORMAT.matcher(email).matches()) {
            warnings.add("email sai định dạng: " + email);
        }
    }

    private void checkUrls(CandidateProfile p, List<String> warnings) {
        List<String> urls = new ArrayList<>();
        if (p.getPersonal_info() != null && p.getPersonal_info().getGithub_url() != null) {
            urls.add(p.getPersonal_info().getGithub_url());
        }
        if (p.getPersonal_projects() != null) {
            for (CandidateProfile.PersonalProject pr : p.getPersonal_projects()) {
                if (pr.getGithub_url() != null) {
                    urls.add(pr.getGithub_url());
                }
            }
        }
        for (String url : urls) {
            if (!URL_FORMAT.matcher(url).matches()) {
                warnings.add("URL đáng ngờ (giữ nguyên giá trị nguồn): " + url);
            }
        }
    }

    private void checkDates(CandidateProfile p, List<String> warnings) {
        if (p.getExperience() != null) {
            for (CandidateProfile.Experience e : p.getExperience()) {
                checkOrder(e.getStart_date(), e.getEnd_date(),
                        "experience@" + e.getCompany(), warnings);
            }
        }
        if (p.getPersonal_projects() != null) {
            for (CandidateProfile.PersonalProject pr : p.getPersonal_projects()) {
                checkOrder(pr.getStart_date(), pr.getEnd_date(),
                        "project@" + pr.getName(), warnings);
            }
        }
    }

    /** So sánh được khi cả hai đều ở dạng MM/YYYY số. Các dạng khác bỏ qua. */
    private void checkOrder(String start, String end, String where, List<String> warnings) {
        int[] s = parseMonthYear(start);
        int[] e = parseMonthYear(end);
        if (s != null && e != null && (e[0] * 12 + e[1] < s[0] * 12 + s[1])) {
            warnings.add("ngày kết thúc trước ngày bắt đầu ở " + where
                    + " (" + start + " > " + end + ")");
        }
    }

    private int[] parseMonthYear(String s) {
        if (s == null) {
            return null;
        }
        java.util.regex.Pattern p = java.util.regex.Pattern.compile("(\\d{1,2})[/-](\\d{4})");
        var matcher = p.matcher(s);
        if (!matcher.find()) {
            return null;
        }
        try {
            return new int[]{Integer.parseInt(matcher.group(2)), Integer.parseInt(matcher.group(1))};
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private void checkGpa(CandidateProfile p, List<String> warnings) {
        if (p.getEducation() == null) {
            return;
        }
        for (CandidateProfile.Education e : p.getEducation()) {
            String gpa = e.getGpa();
            if (gpa == null) {
                continue;
            }
            var m = Pattern.compile("(\\d+[.,]\\d+)\\s*/\\s*(\\d+[.,]\\d+)").matcher(gpa);
            if (!m.find()) {
                continue;
            }
            try {
                double v = Double.parseDouble(m.group(1).replace(',', '.'));
                double scale = Double.parseDouble(m.group(2).replace(',', '.'));
                if (v < 0 || v > scale) {
                    warnings.add("GPA vượt miền thang điểm (" + gpa + ") ở " + e.getSchool());
                }
            } catch (NumberFormatException ignored) {
            }
        }
    }

    /** Chỉ loại trùng Y HỆT trong cùng một description list. */
    private void dedupDescriptions(CandidateProfile p, List<String> warnings) {
        if (p.getExperience() != null) {
            for (CandidateProfile.Experience e : p.getExperience()) {
                if (e.getDescription() != null) {
                    dedup(e.getDescription(), "experience@" + e.getCompany(), warnings);
                }
            }
        }
    }

    private void dedup(List<String> items, String where, List<String> warnings) {
        Set<String> seen = new HashSet<>();
        List<String> keep = new ArrayList<>();
        for (String item : items) {
            if (item == null || !seen.add(item.strip())) {
                if (item != null) {
                    warnings.add("loại bullet trùng y hệt ở " + where);
                }
                continue;
            }
            keep.add(item);
        }
        items.clear();
        items.addAll(keep);
    }
}
