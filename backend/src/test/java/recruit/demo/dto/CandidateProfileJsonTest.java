package recruit.demo.dto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

/** Contract test: the profile holds only CV fields; enrichment fields are ignored (synthetic data only). */
class CandidateProfileJsonTest {

    private final JsonMapper mapper = JsonMapper.builder().build();

    private static final String WITH_ENRICHMENT = """
            {
              "personal_info": {"full_name": "Test Synthetic", "email": "t@example.test", "phone": null, "github_url": null},
              "objective": null,
              "education": [{"school": "PTIT", "major": "CNTT", "start_year": "2020", "end_year": 2024, "gpa": "3.2",
                             "school_normalized": {"id": 13, "name": "Học viện Công nghệ Bưu chính Viễn thông"}}],
              "experience": [], "personal_projects": [],
              "skills": ["Spring Boot", "Postgress"],
              "certificates": [], "honours": [], "languages": [],
              "skills_normalized": [{"raw": "Spring Boot", "id": 500, "name": "Spring Boot", "category": "Framework/Library", "method": "exact"}],
              "implied_skills": [{"id": 300, "name": "Java", "category": "Programming Language", "via": [{"from": "Spring Boot", "rel": "REQUIRES"}]}],
              "skills_detected": [{"id": 500, "name": "Spring Boot", "category": "Framework/Library", "source": "both"}],
              "flags": [{"code": "SKILLS_UNLINKED", "count": 1, "field": "skills"}]
            }
            """;

    @Test
    void ignoresEnrichmentFields() throws Exception {
        CandidateProfile p = mapper.readValue(WITH_ENRICHMENT, CandidateProfile.class);

        assertEquals(2, p.getSkills().size());
        assertEquals("PTIT", p.getEducation().get(0).getSchool());
        assertEquals(2020, p.getEducation().get(0).getStart_year());

        String json = mapper.writeValueAsString(p);
        for (String key : new String[] {"skills_normalized", "implied_skills", "school_normalized", "skills_detected", "flags"}) {
            assertFalse(json.contains("\"" + key + "\""), key);
        }
    }

    @Test
    void parsesLegacyHonorsAlias() throws Exception {
        String legacy = """
                {"personal_info": {"full_name": "Test Synthetic"}, "education": [{"school": "Trường lạ"}],
                 "skills": ["Java"], "honors": ["Giải Nhất"]}
                """;
        CandidateProfile p = mapper.readValue(legacy, CandidateProfile.class);

        assertEquals("Giải Nhất", p.getHonours().get(0));
        assertEquals("Trường lạ", p.getEducation().get(0).getSchool());
    }

    @Test
    void descriptionListsStayMutable() {
        CandidateProfile.Experience e = new CandidateProfile.Experience();
        e.setDescription(new java.util.ArrayList<>());
        e.getDescription().add("bullet");
        e.getDescription().clear();
        CandidateProfile.PersonalProject p = new CandidateProfile.PersonalProject();
        p.setDescription(java.util.List.of("a"));
        p.getDescription().add("b");
        assertEquals(2, p.getDescription().size());
    }
}
