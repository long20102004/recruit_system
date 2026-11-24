package recruit.demo.service.cvmatch;

import org.junit.jupiter.api.Test;
import recruit.demo.entity.JobStatus;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

class CvMatchPayloadsTest {
    private final ObjectMapper mapper = new ObjectMapper();

    @SuppressWarnings("unchecked")
    private Map<String, Object> extracted() {
        return mapper.readValue("""
            {"personal_info":{"full_name":"A","email":"cv@x.test","phone":"0900"},
             "objective":"cu",
             "experience":[{"company":"Cty A","job_title":"Backend Dev","start_date":"03/2022","end_date":null},
                           {"company":"Cty B","job_title":"Java Dev","start_date":"07/2019","end_date":"02/2022"}],
             "education":[{"school":"BK","major":"KHMT","start_year":"2015","end_year":"2019"}],
             "skills":["Java"],"certificates":[],
             "implied_skills":[{"name":"JVM"}],"skills_normalized":[],"flags":["x"]}
            """, Map.class);
    }

    @Test
    void cvUsesAccountEmailDropsKgAndKeepsDatesWhenTitlesEdited() {
        Map<String, List<String>> form = new LinkedHashMap<>();
        form.put("Kỹ năng", List.of("Java, Spring Boot", "Docker;Java"));
        form.put("Tóm tắt", List.of("Dong 1", "Dong 2"));
        form.put("Kinh nghiệm", List.of("Senior Backend Dev — Cty A", "Java Dev — Cty B"));
        var cv = CvMatchPayloads.cvPayload(extracted(), form, " acct@x.test ", "Hà Nội");

        assertEquals("acct@x.test", ((Map<?, ?>) cv.get("personal_info")).get("email"));
        assertEquals("Hà Nội", cv.get("location"));
        CvMatchPayloads.KG_FIELDS.forEach(f -> assertFalse(cv.containsKey(f), f));
        assertEquals(List.of("Java", "Spring Boot", "Docker"), cv.get("skills"));
        assertEquals("Dong 1\nDong 2", cv.get("objective"));
        var exp = (List<Map<String, Object>>) cv.get("experience");
        assertEquals("Senior Backend Dev", exp.get(0).get("job_title"));
        assertEquals("03/2022", exp.get(0).get("start_date"));          // ngay giu nguyen
        assertTrue(exp.get(0).containsKey("end_date") && exp.get(0).get("end_date") == null);
        assertEquals(1, ((List<?>) cv.get("education")).size());       // truong khong co tren form: giu ban trich xuat
    }

    @Test
    void removedExperienceLinesDropItemsAndNewLinesHaveNoDates() {
        var none = CvMatchPayloads.cvPayload(extracted(), Map.of("Kinh nghiệm", List.of()), "a@x", null);
        assertEquals(List.of(), none.get("experience"));                  // xoa het -> 0 nam kinh nghiem

        var cv = CvMatchPayloads.cvPayload(extracted(),
                Map.of("Kinh nghiệm", List.of("Java Dev — Cty B", "Tester — Cty C", "Freelancer")), "a@x", null);
        var exp = (List<Map<String, Object>>) cv.get("experience");
        assertEquals(3, exp.size());
        assertEquals("07/2019", exp.get(0).get("start_date"));          // khop nguyen dong -> giu ca ngay
        assertEquals("Cty C", exp.get(1).get("company"));
        assertFalse(exp.get(1).containsKey("start_date"));
        assertEquals("Freelancer", exp.get(2).get("job_title"));
    }

    @Test
    void doesNotMutateInput() {
        var src = extracted();
        CvMatchPayloads.cvPayload(src, Map.of("Kinh nghiệm", List.of("X — Y", "Z — W")), "a@x", null);
        assertEquals("cv@x.test", ((Map<?, ?>) src.get("personal_info")).get("email"));
        assertEquals("Backend Dev", ((Map<?, ?>) ((List<?>) src.get("experience")).get(0)).get("job_title"));
    }

    @Test
    void jdPayloadMapsJobTableWithoutStatus() {
        var jd = CvMatchPayloads.jdPayload(7, "Java Developer", "Cong ty phan mem", "Hà Nội (Hybrid)", "Full-time",
                new BigDecimal("2.0"), "- Phat trien API\n• Review code", "Biet Spring\n\n", null,
                List.of(new CvMatchPayloads.JobSkillItem("Java", true), new CvMatchPayloads.JobSkillItem(" java ", false),
                        new CvMatchPayloads.JobSkillItem("Docker", false)));
        assertEquals("job-7", jd.get("jd_id"));
        assertEquals("hybrid", jd.get("work_mode"));
        assertEquals(2.0, jd.get("min_years"));
        assertEquals(List.of("Phat trien API", "Review code"), jd.get("responsibilities"));
        assertEquals(List.of("Biet Spring"), jd.get("requirements"));
        assertEquals(2, ((List<?>) jd.get("skills")).size());           // trung ten (khong phan biet hoa) bi bo
        assertFalse(jd.containsKey("status"));
        assertEquals(7, CvMatchPayloads.jobIdOf("job-7"));
        assertNull(CvMatchPayloads.jobIdOf("E2E-JAVA"));
        assertEquals("open", CvMatchPayloads.jdStatus(JobStatus.PUBLISHED));
        assertEquals("draft", CvMatchPayloads.jdStatus(JobStatus.DRAFT));
        assertEquals("closed", CvMatchPayloads.jdStatus(JobStatus.CLOSED));
    }

    @Test
    void hashIgnoresKeyOrder() {
        Map<String, Object> a = new LinkedHashMap<>(), b = new LinkedHashMap<>();
        a.put("x", 1); a.put("y", Map.of("p", List.of(1, 2), "q", "s"));
        b.put("y", new TreeMap<>(Map.of("q", "s", "p", List.of(1, 2)))); b.put("x", 1);
        assertEquals(CvMatchPayloads.contentHash(mapper, a), CvMatchPayloads.contentHash(mapper, b));
        b.put("x", 2);
        assertNotEquals(CvMatchPayloads.contentHash(mapper, a), CvMatchPayloads.contentHash(mapper, b));
    }
}
