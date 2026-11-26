package recruit.demo.service.cv;

import org.junit.jupiter.api.Test;
import recruit.demo.service.cvmatch.CvMatchPayloads;
import tools.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/** Field mở rộng (V8) và việc matching vẫn tách đúng dòng Học vấn / Kinh nghiệm có phần chi tiết. */
class CvProfileFieldsTest {

    private static final String PROFILE = """
            {"personal_info":{"full_name":"A","email":"a@x.test","phone":"0900","github_url":"https://github.com/a"},
             "objective":"Backend",
             "education":[{"school":"PTIT","major":"Information Technology","start_year":2022,"end_year":2027,"gpa":"3.33/4.0"}],
             "experience":[{"company":"TLH","job_title":null,"start_date":"October 2025","end_date":"May 2026",
                            "description":["Built REST APIs","Optimized SQL"]},
                           {"company":"Example","job_title":"Intern","start_date":null,"end_date":null,"description":"Wrote tests"}],
             "personal_projects":[{"name":"BOOKSTORE","role":"Developer","team_size":1,"start_date":"May 2025",
                                   "end_date":"June 2025","github_url":"https://github.com/a/b","tech_stack":["Spring Boot","MySQL"]}],
             "skills":["Java"],"certificates":[],"honours":["Full scholarship"],
             "languages":[{"language":"English","note":"TOEIC 690"},"Japanese"]}
            """;

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void mapsExtendedFields() {
        Map<String, List<String>> f = new CvProfileMapper().fields(mapper.readTree(PROFILE));
        assertEquals(List.of("https://github.com/a"), f.get("GitHub"));
        assertEquals(List.of("Information Technology — PTIT | 2022–2027 | GPA 3.33/4.0"), f.get("Học vấn"));
        assertEquals(List.of("— TLH | October 2025–May 2026", "Intern — Example"), f.get("Kinh nghiệm"));
        assertEquals(List.of("TLH: Built REST APIs", "TLH: Optimized SQL", "Example: Wrote tests"), f.get("Mô tả kinh nghiệm"));
        assertEquals(List.of("BOOKSTORE — Developer | May 2025–June 2025 | 1 người | Công nghệ: Spring Boot, MySQL"
                + " | https://github.com/a/b"), f.get("Dự án"));
        assertEquals(List.of("Full scholarship"), f.get("Giải thưởng"));
        assertEquals(List.of("English — TOEIC 690", "Japanese"), f.get("Ngoại ngữ"));
    }

    @Test
    void matchingStillSplitsLinesWithDetails() {
        Map<String, Object> extracted = mapper.readValue(PROFILE, Map.class);
        Map<String, List<String>> form = new CvProfileMapper().fields(mapper.readTree(PROFILE));
        Map<String, Object> cv = CvMatchPayloads.cvPayload(extracted, Map.of(
                "Học vấn", form.get("Học vấn"), "Kinh nghiệm", form.get("Kinh nghiệm")), "a@x.test", null);

        @SuppressWarnings("unchecked") var edu = (List<Map<String, Object>>) cv.get("education");
        assertEquals("PTIT", edu.get(0).get("school"));
        assertEquals("Information Technology", edu.get(0).get("major"));
        assertEquals(2022, edu.get(0).get("start_year"));

        @SuppressWarnings("unchecked") var exp = (List<Map<String, Object>>) cv.get("experience");
        assertNull(exp.get(0).get("job_title"), "missing title must not become the company name");
        assertEquals("TLH", exp.get(0).get("company"));
        assertEquals("October 2025", exp.get(0).get("start_date"));
        assertEquals("Intern", exp.get(1).get("job_title"));
        assertEquals("Example", exp.get(1).get("company"));
    }

    @Test
    void editedLineWithDifferentCountStillMatchesExtractedItem() {
        Map<String, Object> extracted = mapper.readValue(PROFILE, Map.class);
        // người dùng xoá mục thứ hai, giữ mục có chi tiết
        Map<String, Object> cv = CvMatchPayloads.cvPayload(extracted,
                Map.of("Kinh nghiệm", List.of("— TLH | October 2025–May 2026")), "a@x.test", null);
        @SuppressWarnings("unchecked") var exp = (List<Map<String, Object>>) cv.get("experience");
        assertEquals(1, exp.size());
        assertEquals("TLH", exp.get(0).get("company"));
        assertEquals(List.of("Built REST APIs", "Optimized SQL"), exp.get(0).get("description"));
    }
}
