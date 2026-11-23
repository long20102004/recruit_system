package recruit.demo.service.cv;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;
import static org.junit.jupiter.api.Assertions.*;
class CvProfileMapperTest {
    @Test void projectsExtractedProfileIntoEditableFields() {
        var profile = new ObjectMapper().readTree("""
            {"personal_info":{"full_name":"Test Candidate","email":"test@example.com"},
             "skills":["Java","Spring Boot"],"education":[{"major":"Computer Science","school":"PTIT"}],
             "experience":[{"company":"Example","job_title":"Developer"}],"certificates":[]}
            """);
        var fields = new CvProfileMapper().fields(profile);
        assertEquals(java.util.List.of("Java", "Spring Boot"), fields.get("Kỹ năng"));
        assertEquals(java.util.List.of("Developer — Example"), fields.get("Kinh nghiệm"));
        assertEquals(java.util.List.of("Computer Science — PTIT"), fields.get("Học vấn"));
        assertTrue(fields.get("Điện thoại").isEmpty());
        assertTrue(fields.get("Tóm tắt").isEmpty());
    }
    @Test void missingDataNeverBecomesPrototypeExperience() {
        var fields = new CvProfileMapper().fields(new ObjectMapper().readTree("{}"));
        assertTrue(fields.values().stream().allMatch(java.util.List::isEmpty));
    }
    @Test void malformedPdfIsRejectedBeforeCallingAi() {
        var module = new CvExtractionModule(null, "http://unused");
        var error = assertThrows(recruit.demo.exception.ApiException.class, () -> module.extract(new byte[]{1,2,3}));
        assertEquals(400, error.getStatus().value());
    }
}
