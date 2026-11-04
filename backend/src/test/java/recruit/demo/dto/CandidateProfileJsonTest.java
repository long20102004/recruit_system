package recruit.demo.dto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

/** Contract test for the additive KG fields of feature 005 (synthetic data only). */
class CandidateProfileJsonTest {

    private final JsonMapper mapper = JsonMapper.builder().build();

    private static final String ENRICHED = """
            {
              "personal_info": {"full_name": "Test Synthetic", "email": "t@example.test", "phone": null, "github_url": null},
              "objective": null,
              "education": [{"school": "PTIT", "major": "CNTT", "start_year": "2020", "end_year": 2024, "gpa": "3.2",
                             "school_normalized": {"id": 13, "name": "Học viện Công nghệ Bưu chính Viễn thông"}}],
              "experience": [], "personal_projects": [],
              "skills": ["Spring Boot", "Postgress", "Chịu áp lực tốt"],
              "certificates": [], "honours": [], "languages": [],
              "skills_normalized": [
                {"raw": "Spring Boot", "id": 500, "name": "Spring Boot", "category": "Framework/Library", "method": "exact"},
                {"raw": "Postgress", "id": 431, "name": "PostgreSQL", "category": "Database", "method": "fuzzy"},
                {"raw": "Chịu áp lực tốt", "id": null, "name": null, "category": null, "method": "unlinked"}
              ],
              "implied_skills": [
                {"id": 300, "name": "Java", "category": "Programming Language", "via": [{"from": "Spring Boot", "rel": "REQUIRES"}]}
              ],
              "flags": [
                {"code": "UNGROUNDED_REMOVED", "count": 2, "field": null},
                {"code": "SKILLS_UNLINKED", "count": 1, "field": "skills"}
              ]
            }
            """;

    @Test
    void parsesEnrichedFields() throws Exception {
        CandidateProfile p = mapper.readValue(ENRICHED, CandidateProfile.class);

        assertEquals(3, p.getSkills_normalized().size());
        assertEquals("PostgreSQL", p.getSkills_normalized().get(1).getName());
        assertEquals("unlinked", p.getSkills_normalized().get(2).getMethod());
        assertNull(p.getSkills_normalized().get(2).getId());
        assertEquals("REQUIRES", p.getImplied_skills().get(0).getVia().get(0).getRel());
        assertEquals("Học viện Công nghệ Bưu chính Viễn thông",
                p.getEducation().get(0).getSchool_normalized().getName());
        assertEquals("skills", p.getFlags().get(1).getField());
        assertEquals(2020, p.getEducation().get(0).getStart_year());
        assertEquals(3, p.getSkills().size()); // implied skills never merged into skills
    }

    @Test
    void parsesLegacyResponseWithoutNewFields() throws Exception {
        String legacy = """
                {"personal_info": {"full_name": "Test Synthetic"}, "education": [{"school": "Trường lạ"}],
                 "skills": ["Java"], "honors": ["Giải Nhất"]}
                """;
        CandidateProfile p = mapper.readValue(legacy, CandidateProfile.class);

        assertNull(p.getSkills_normalized());
        assertNull(p.getImplied_skills());
        assertNull(p.getFlags());
        assertNull(p.getEducation().get(0).getSchool_normalized());
        assertEquals("Giải Nhất", p.getHonours().get(0));
    }

    @Test
    void serializesSnakeCaseKeys() throws Exception {
        CandidateProfile p = mapper.readValue(ENRICHED, CandidateProfile.class);
        String json = mapper.writeValueAsString(p);

        assertTrue(json.contains("\"skills_normalized\""));
        assertTrue(json.contains("\"implied_skills\""));
        assertTrue(json.contains("\"school_normalized\""));
    }
}
