package recruit.demo.service.cv;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

/**
 * Tách profile Module 1 (CandidateProfile) thành các field của form / cv_data (danh sách trong setting CV_FIELD).
 * Học vấn, Kinh nghiệm: "a — b" ({@link #JOIN}, CvMatchPayloads tách lại để gửi cvmatch), chi tiết thêm sau
 * {@link #DETAIL}. Khi thiếu vế đầu vẫn giữ dấu nối ("— Công ty") để không bị hiểu nhầm là vế đầu.
 */
@Component
public class CvProfileMapper {
    public static final String JOIN = " — ";
    /** Ngăn phần chi tiết (thời gian, GPA, số người…) ở cuối dòng; CvMatchPayloads bỏ phần này trước khi tách. */
    public static final String DETAIL = " | ";

    public Map<String, List<String>> fields(JsonNode profile) {
        Map<String, List<String>> fields = new LinkedHashMap<>();
        var personal = profile.path("personal_info");
        fields.put("Họ tên", scalar(personal.path("full_name")));
        fields.put("Email", scalar(personal.path("email")));
        fields.put("Điện thoại", scalar(personal.path("phone")));
        fields.put("GitHub", scalar(personal.path("github_url")));
        fields.put("Tóm tắt", scalar(profile.path("objective")));
        fields.put("Kỹ năng", strings(profile.path("skills")));
        List<String> implied = new ArrayList<>();
        for (var item : profile.path("implied_skills")) {
            String name = text(item.path("name"));
            if (!name.isBlank()) implied.add(name);
        }
        fields.put("Kỹ năng suy ra", implied);

        List<String> education = new ArrayList<>();
        for (var item : profile.path("education")) {
            String gpa = text(item.path("gpa"));
            education.add(line(join(item, "major", "school"),
                    period(item.path("start_year"), item.path("end_year")), gpa.isBlank() ? "" : "GPA " + gpa));
        }
        fields.put("Học vấn", education);

        List<String> experience = new ArrayList<>();
        List<String> duties = new ArrayList<>();
        for (var item : profile.path("experience")) {
            String head = join(item, "job_title", "company");
            experience.add(line(head, period(item.path("start_date"), item.path("end_date"))));
            String where = Stream.of(text(item.path("company")), text(item.path("job_title")))
                    .filter(s -> !s.isBlank()).findFirst().orElse("");
            for (String duty : strings(item.path("description"))) {
                duties.add(where.isBlank() ? duty : where + ": " + duty);
            }
        }
        fields.put("Kinh nghiệm", experience);
        fields.put("Mô tả kinh nghiệm", duties);

        List<String> projects = new ArrayList<>();
        for (var item : profile.path("personal_projects")) {
            String name = text(item.path("name"));
            String role = text(item.path("role"));
            String head = name.isBlank() && role.isBlank() ? "" : join(item, "name", "role");
            String team = text(item.path("team_size"));
            List<String> tech = strings(item.path("tech_stack"));
            projects.add(line(head, period(item.path("start_date"), item.path("end_date")),
                    team.isBlank() ? "" : team + " người",
                    tech.isEmpty() ? "" : "Công nghệ: " + String.join(", ", tech),
                    text(item.path("github_url"))));
        }
        fields.put("Dự án", projects);

        fields.put("Chứng chỉ", strings(profile.path("certificates")));
        fields.put("Giải thưởng", strings(profile.path("honours")));
        List<String> languages = new ArrayList<>();
        for (var item : profile.path("languages")) {
            String lang = item.isObject() ? text(item.path("language")) : text(item);
            String note = item.isObject() ? text(item.path("note")) : "";
            if (!lang.isBlank()) languages.add(note.isBlank() ? lang : lang + JOIN + note);
        }
        fields.put("Ngoại ngữ", languages);
        return fields;
    }

    /** "a — b"; thiếu a thì "— b" (giữ vị trí từng vế), thiếu b thì "a". */
    private String join(JsonNode node, String a, String b) {
        String first = text(node.path(a));
        String second = text(node.path(b));
        if (first.isBlank()) return second.isBlank() ? "" : JOIN.strip() + " " + second;
        return second.isBlank() ? first : first + JOIN + second;
    }

    /** Ghép vế chính với các chi tiết khác rỗng bằng {@link #DETAIL}; bỏ dòng hoàn toàn rỗng ở nơi gọi không cần. */
    private static String line(String head, String... details) {
        List<String> parts = new ArrayList<>();
        if (!head.isBlank()) parts.add(head);
        for (String d : details) if (d != null && !d.isBlank()) parts.add(d);
        return String.join(DETAIL, parts);
    }

    private static String period(JsonNode start, JsonNode end) {
        String a = text(start);
        String b = text(end);
        if (a.isBlank() && b.isBlank()) return "";
        return (a.isBlank() ? "?" : a) + "–" + (b.isBlank() ? "nay" : b);
    }

    private List<String> scalar(JsonNode node) { String value = text(node); return value.isBlank() ? List.of() : List.of(value); }
    public static String text(JsonNode node) { return node.isMissingNode() || node.isNull() ? "" : node.asString().trim(); }
    /** Mảng chuỗi; AI đôi khi trả một chuỗi đơn thay vì mảng (giống ACCEPT_SINGLE_VALUE_AS_ARRAY của DTO). */
    public static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        if (array.isArray()) for (var item : array) { String value = text(item); if (!value.isBlank()) result.add(value); }
        else if (array.isString() && !text(array).isBlank()) result.add(text(array));
        return result;
    }
}
