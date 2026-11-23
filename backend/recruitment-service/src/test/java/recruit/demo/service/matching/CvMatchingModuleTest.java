package recruit.demo.service.matching;
import org.junit.jupiter.api.Test;
import recruit.demo.client.AiJsonClient;
import tools.jackson.databind.*;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
class CvMatchingModuleTest {
    private CvMatchingModule module(String json) {
        var mapper = new ObjectMapper();
        return new CvMatchingModule(new AiJsonClient(mapper) {
            @Override public JsonNode post(String url, Object body) {
                assertEquals("http://match/match/no-llm", url);
                assertTrue(((Map<?,?>)body).containsKey("candidate"));
                assertTrue(((Map<?,?>)body).containsKey("jd"));
                return mapper.readTree(json);
            }
        }, "http://match");
    }
    @Test void acceptsScoresFromIndependentMatchingService() {
        var result = module("""
            {"score":82.5,"feature_scores":{"skill":1,"experience":0.5,"education":1,"context":0.5},
             "matched_skills":["java"],"missing_skills":[]}
            """).match(Map.of("skills", java.util.List.of("Java")), Map.of("required_skills", java.util.List.of("Java")));
        assertEquals(82.5, result.path("score").asDouble());
    }
    @Test void missingFeatureScoresAreRejectedInsteadOfSavedAsZeros() {
        var error = assertThrows(recruit.demo.exception.ApiException.class,
            () -> module("{\"score\":90,\"feature_scores\":{}}").match(Map.of(), Map.of()));
        assertEquals(502, error.getStatus().value());
    }
}
