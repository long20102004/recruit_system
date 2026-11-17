package recruit.demo.service.matching;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.http.HttpStatus;
import recruit.demo.client.AiJsonClient;
import recruit.demo.exception.ApiException;
import recruit.demo.service.cv.CvProfileMapper;
import tools.jackson.databind.JsonNode;
import java.util.*;
@Service
public class CvMatchingModule {
    private final AiJsonClient http;
    private final String url;
    public CvMatchingModule(AiJsonClient http, @Value("${app.cv-matching.base-url}") String url) {
        this.http = http; this.url = url;
    }
    public JsonNode match(Map<String,Object> candidate, Map<String,Object> jd) {
        var result = http.post(url + "/match/no-llm", Map.of("candidate", candidate, "jd", jd));
        if (!result.path("score").isNumber() || !result.path("feature_scores").isObject())
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Matching service returned an invalid score");
        for (String name : java.util.List.of("skill", "experience", "education", "context")) {
            var value = result.path("feature_scores").path(name);
            if (!value.isNumber() || !Double.isFinite(value.asDouble()) || value.asDouble() < 0 || value.asDouble() > 1)
                throw new ApiException(HttpStatus.BAD_GATEWAY, "Invalid matching feature: " + name);
        }
        if (!result.path("matched_skills").isArray() || !result.path("missing_skills").isArray())
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Invalid matching skill lists");
        double score = result.path("score").asDouble();
        if (!Double.isFinite(score) || score < 0 || score > 100)
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Matching score must be between 0 and 100");
        return result;
    }
}
