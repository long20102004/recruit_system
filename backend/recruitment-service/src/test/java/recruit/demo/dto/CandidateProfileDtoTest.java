package recruit.demo.dto;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/** Response của POST /api/cvs: cùng cấu trúc JSON với CandidateProfile của /analyze-pdf (nhánh hocnv/DO-06). */
class CandidateProfileDtoTest {

    private final ObjectMapper mapper = new ObjectMapper();

    /** Dạng ai-service trả về: có trường KG thừa, năm dạng chuỗi, mô tả là chuỗi đơn, ngôn ngữ lẫn chuỗi và object. */
    private static final String AI_DATA = """
            {"personal_info":{"full_name":"Test Candidate","email":"test@example.com","phone":"0900000000",
                              "github_url":"https://github.com/test"},
             "objective":"Backend developer",
             "education":[{"school":"PTIT","major":"Computer Science","start_year":"2020","end_year":"2024 (dự kiến)","gpa":"3.2/4"}],
             "experience":{"company":"Example","job_title":"Intern","start_date":"06/2023","end_date":"09/2023",
                           "description":"Built REST APIs"},
             "personal_projects":[{"name":"HireLens","role":"Backend","team_size":"4 người","tech_stack":["Java","Spring Boot"],
                                   "description":["Auth","Gateway"]}],
             "skills":["Java","Spring Boot"],
             "certificates":"TOEIC 800",
             "honors":["Top 10 hackathon"],
             "languages":["English",{"language":"Japanese","note":"N3"}],
             "implied_skills":[{"skill":"SQL","reason":"from Spring Data"}],
             "kg":{"nodes":3}}
            """;

    @Test
    void readsAiPayloadIntoProfileDto() {
        CandidateProfileDto p = mapper.readValue(AI_DATA, CandidateProfileDto.class);

        assertEquals("Test Candidate", p.getPersonal_info().getFull_name());
        assertEquals("https://github.com/test", p.getPersonal_info().getGithub_url());
        assertEquals("Backend developer", p.getObjective());
        assertEquals(2020, p.getEducation().get(0).getStart_year());
        assertEquals(2024, p.getEducation().get(0).getEnd_year());
        assertEquals("3.2/4", p.getEducation().get(0).getGpa());
        assertEquals(1, p.getExperience().size(), "single object accepted as array");
        assertEquals(List.of("Built REST APIs"), p.getExperience().get(0).getDescription());
        assertEquals(4, p.getPersonal_projects().get(0).getTeam_size());
        assertEquals(List.of("Java", "Spring Boot"), p.getPersonal_projects().get(0).getTech_stack());
        assertEquals(List.of("TOEIC 800"), p.getCertificates());
        assertEquals(List.of("Top 10 hackathon"), p.getHonours(), "honors alias");
        assertEquals("English", p.getLanguages().get(0).getLanguage());
        assertEquals("N3", p.getLanguages().get(1).getNote());
    }

    @Test
    void serializesWithAnalyzePdfFieldNamesAndDropsKgFields() {
        String json = mapper.writeValueAsString(mapper.readValue(AI_DATA, CandidateProfileDto.class));
        for (String key : List.of("\"personal_info\"", "\"full_name\"", "\"github_url\"", "\"objective\"",
                "\"education\"", "\"start_year\"", "\"experience\"", "\"job_title\"", "\"personal_projects\"",
                "\"team_size\"", "\"tech_stack\"", "\"skills\"", "\"certificates\"", "\"honours\"", "\"languages\"")) {
            assertTrue(json.contains(key), key + " missing in " + json);
        }
        assertFalse(json.contains("implied_skills"));
        assertFalse(json.contains("\"kg\""));
    }

    @Test
    void wrapsInBaseResponse() {
        String json = mapper.writeValueAsString(BaseResponse.success(new CandidateProfileDto()));
        assertTrue(json.contains("\"code\":200"), json);
        assertTrue(json.contains("\"message\":\"Success\""), json);
        assertTrue(json.contains("\"data\":{"), json);
    }
}
