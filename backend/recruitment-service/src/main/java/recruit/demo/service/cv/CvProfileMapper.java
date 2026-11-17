package recruit.demo.service.cv;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import java.util.*;
@Component
public class CvProfileMapper {
    public Map<String, List<String>> fields(JsonNode profile) {
        Map<String, List<String>> fields = new LinkedHashMap<>();
        var personal = profile.path("personal_info");
        fields.put("Họ tên", scalar(personal.path("full_name")));
        fields.put("Email", scalar(personal.path("email")));
        fields.put("Điện thoại", scalar(personal.path("phone")));
        fields.put("Tóm tắt", scalar(profile.path("objective")));
        fields.put("Kỹ năng", strings(profile.path("skills")));
        List<String> implied = new ArrayList<>();
        for (var item : profile.path("implied_skills")) {
            String name = text(item.path("name"));
            if (!name.isBlank()) implied.add(name);
        }
        fields.put("Kỹ năng suy ra", implied);
        fields.put("Chứng chỉ", strings(profile.path("certificates")));
        List<String> education = new ArrayList<>();
        for (var item : profile.path("education")) education.add(join(item, "major", "school"));
        fields.put("Học vấn", education);
        List<String> experience = new ArrayList<>();
        for (var item : profile.path("experience")) experience.add(join(item, "job_title", "company"));
        fields.put("Kinh nghiệm", experience);
        return fields;
    }
    private String join(JsonNode node, String a, String b) {
        return String.join(" — ", java.util.stream.Stream.of(text(node.path(a)), text(node.path(b)))
            .filter(s -> !s.isBlank()).toList());
    }
    private List<String> scalar(JsonNode node) { String value = text(node); return value.isBlank() ? List.of() : List.of(value); }
    public static String text(JsonNode node) { return node.isMissingNode() || node.isNull() ? "" : node.asString(); }
    public static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        if (array.isArray()) for (var item : array) { String value = text(item); if (!value.isBlank()) result.add(value); }
        return result;
    }
}
