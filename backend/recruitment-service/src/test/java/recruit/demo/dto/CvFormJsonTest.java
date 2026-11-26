package recruit.demo.dto;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/** CvFormResponse, ConfirmCvRequest, CvFieldValue (Lombok): JSON giữ đúng tên khoá như khi còn là record, FE không phải đổi. */
class CvFormJsonTest {

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    void formResponseKeepsJsonNames() {
        var res = CvFormResponse.builder()
                .fileName("cv.pdf").parsingStatus("COMPLETED").analyzed(true)
                .fields(List.of(new CvFieldValue("Kỹ năng", List.of("Java"))))
                .profile(new CandidateProfileDto())
                .build();
        String json = mapper.writeValueAsString(res);
        assertTrue(json.contains("\"fileName\":\"cv.pdf\""), json);
        assertTrue(json.contains("\"parsingStatus\":\"COMPLETED\""), json);
        assertTrue(json.contains("\"analyzed\":true"), json);
        assertTrue(json.contains("\"fields\":[{\"field\":\"Kỹ năng\",\"values\":[\"Java\"]}]"), json);
        assertTrue(json.contains("\"profile\":{"), json);
    }

    @Test
    void confirmRequestReadsFrontendBody() {
        var req = mapper.readValue("""
                {"profile":{"personal_info":{"full_name":"A"},"skills":["Java"]},
                 "fields":[{"field":"Kỹ năng suy ra","values":["SQL"]}]}
                """, ConfirmCvRequest.class);
        assertEquals("A", req.getProfile().getPersonal_info().getFull_name());
        assertEquals("Kỹ năng suy ra", req.getFields().get(0).getField());
        assertEquals(List.of("SQL"), req.getFields().get(0).getValues());

        var legacy = mapper.readValue("{\"fields\":[{\"field\":\"Kỹ năng\",\"values\":[\"Java\"]}]}",
                ConfirmCvRequest.class);
        assertNull(legacy.getProfile());
    }
}
