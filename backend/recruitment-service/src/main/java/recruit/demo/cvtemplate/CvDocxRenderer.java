package recruit.demo.cvtemplate;

import com.deepoove.poi.XWPFTemplate;
import com.deepoove.poi.config.Configure;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.CandidateProfileDto.Education;
import recruit.demo.dto.CandidateProfileDto.Experience;
import recruit.demo.dto.CandidateProfileDto.Language;
import recruit.demo.dto.CandidateProfileDto.PersonalInfo;
import recruit.demo.dto.CandidateProfileDto.PersonalProject;
import recruit.demo.exception.ApiException;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.*;

/**
 * Điền dữ liệu {@link CandidateProfileDto} vào file mẫu Word {@code .docx} bằng {@code poi-tl}.
 * Khối lặp rỗng được đặt {@code null} để poi-tl tự ẩn toàn bộ khối {@code {{?section}}...{{/section}}}.
 */
@Component
public class CvDocxRenderer {

    private final Configure configure = Configure.builder().build();

    public byte[] renderDocx(byte[] templateDocxBytes, CandidateProfileDto profile, String cvTitle) {
        if (templateDocxBytes == null || templateDocxBytes.length == 0) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Nội dung file mẫu DOCX rỗng");
        }
        Map<String, Object> data = buildDataMap(profile, cvTitle);
        try (ByteArrayInputStream in = new ByteArrayInputStream(templateDocxBytes);
             XWPFTemplate template = XWPFTemplate.compile(in, configure);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            template.render(data);
            template.write(out);
            return out.toByteArray();
        } catch (IOException | RuntimeException ex) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Không thể điền dữ liệu vào mẫu Word: " + ex.getMessage());
        }
    }

    public Map<String, Object> buildDataMap(CandidateProfileDto profile, String cvTitle) {
        CandidateProfileDto p = profile == null ? new CandidateProfileDto() : profile;
        PersonalInfo info = p.getPersonal_info();

        Map<String, Object> map = new LinkedHashMap<>();
        map.put("full_name", info != null ? safeStr(info.getFull_name()) : "");
        map.put("title", safeStr(cvTitle));
        map.put("email", info != null ? safeStr(info.getEmail()) : "");
        map.put("phone", info != null ? safeStr(info.getPhone()) : "");
        map.put("github", info != null ? safeStr(info.getGithub_url()) : "");
        map.put("objective", safeStr(p.getObjective()));

        List<String> skills = cleanStrings(p.getSkills());
        List<String> certificates = cleanStrings(p.getCertificates());
        List<String> honours = cleanStrings(p.getHonours());

        map.put("skills_text", skills.isEmpty() ? "" : String.join(", ", skills));
        map.put("certificates_text", certificates.isEmpty() ? "" : String.join("\n", certificates));
        map.put("honours_text", honours.isEmpty() ? "" : String.join("\n", honours));

        map.put("experience", mapExperience(p.getExperience()));
        map.put("education", mapEducation(p.getEducation()));
        map.put("projects", mapProjects(p.getPersonal_projects()));
        map.put("languages", mapLanguages(p.getLanguages()));
        map.put("skills", mapValueList(skills));
        map.put("certificates", mapValueList(certificates));
        map.put("honours", mapValueList(honours));

        return map;
    }

    private List<Map<String, Object>> mapExperience(List<Experience> items) {
        if (items == null || items.isEmpty()) return null;
        List<Map<String, Object>> list = new ArrayList<>();
        for (Experience exp : items) {
            if (exp == null) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("job_title", safeStr(exp.getJob_title()));
            row.put("company", safeStr(exp.getCompany()));
            row.put("location", safeStr(exp.getLocation()));
            row.put("start_date", safeStr(exp.getStart_date()));
            row.put("end_date", safeStr(exp.getEnd_date()));
            row.put("description", formatBullets(exp.getDescription()));
            list.add(row);
        }
        return list.isEmpty() ? null : list;
    }

    private List<Map<String, Object>> mapEducation(List<Education> items) {
        if (items == null || items.isEmpty()) return null;
        List<Map<String, Object>> list = new ArrayList<>();
        for (Education edu : items) {
            if (edu == null) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("school", safeStr(edu.getSchool()));
            row.put("major", safeStr(edu.getMajor()));
            row.put("location", safeStr(edu.getLocation()));
            row.put("start_year", edu.getStart_year() != null ? String.valueOf(edu.getStart_year()) : "");
            row.put("end_year", edu.getEnd_year() != null ? String.valueOf(edu.getEnd_year()) : "");
            row.put("gpa", safeStr(edu.getGpa()));
            list.add(row);
        }
        return list.isEmpty() ? null : list;
    }

    private List<Map<String, Object>> mapProjects(List<PersonalProject> items) {
        if (items == null || items.isEmpty()) return null;
        List<Map<String, Object>> list = new ArrayList<>();
        for (PersonalProject pr : items) {
            if (pr == null) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("name", safeStr(pr.getName()));
            row.put("role", safeStr(pr.getRole()));
            row.put("team_size", pr.getTeam_size() != null ? String.valueOf(pr.getTeam_size()) : "");
            row.put("start_date", safeStr(pr.getStart_date()));
            row.put("end_date", safeStr(pr.getEnd_date()));
            row.put("github_url", safeStr(pr.getGithub_url()));
            row.put("tech_stack", String.join(", ", cleanStrings(pr.getTech_stack())));
            row.put("description", formatBullets(pr.getDescription()));
            list.add(row);
        }
        return list.isEmpty() ? null : list;
    }

    private List<Map<String, Object>> mapLanguages(List<Language> items) {
        if (items == null || items.isEmpty()) return null;
        List<Map<String, Object>> list = new ArrayList<>();
        for (Language lang : items) {
            if (lang == null || safeStr(lang.getLanguage()).isEmpty()) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("language", safeStr(lang.getLanguage()));
            row.put("note", safeStr(lang.getNote()));
            list.add(row);
        }
        return list.isEmpty() ? null : list;
    }

    private List<Map<String, Object>> mapValueList(List<String> items) {
        if (items == null || items.isEmpty()) return null;
        List<Map<String, Object>> list = new ArrayList<>();
        for (String item : items) {
            list.add(Map.of("value", item));
        }
        return list.isEmpty() ? null : list;
    }

    private static String formatBullets(List<String> lines) {
        List<String> cleaned = cleanStrings(lines);
        if (cleaned.isEmpty()) return "";
        List<String> formatted = new ArrayList<>(cleaned.size());
        for (String line : cleaned) {
            formatted.add(line.startsWith("•") ? line : "• " + line);
        }
        return String.join("\n", formatted);
    }

    private static List<String> cleanStrings(List<String> items) {
        if (items == null || items.isEmpty()) return List.of();
        return items.stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
    }

    private static String safeStr(String value) {
        return value == null ? "" : value.trim();
    }
}
