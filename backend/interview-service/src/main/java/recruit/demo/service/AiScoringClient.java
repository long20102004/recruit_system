package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import recruit.demo.config.AppProperties;
import recruit.demo.dto.AiScoringDtos;
import recruit.demo.exception.ApiException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class AiScoringClient {

    private final AppProperties appProperties;
    private final ObjectMapper objectMapper;

    public boolean isEnabled() {
        return appProperties.getAi().isEnabled();
    }

    /**
     * Call AI evaluate with inline barem. Throws if AI fails (no silent fallback).
     */
    public AiScoringDtos.EvaluateResult evaluate(
            String answer,
            String questionText,
            String referenceAnswer,
            List<AiScoringDtos.CriterionIn> criteria,
            String questionIdLabel
    ) {
        if (!isEnabled()) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Chấm điểm AI đang tắt (app.ai.enabled=false).");
        }
        if (answer == null || answer.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Câu trả lời trống.");
        }
        if (referenceAnswer == null || referenceAnswer.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Câu hỏi thiếu đáp án mẫu — không chấm AI được.");
        }
        if (criteria == null || criteria.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Câu hỏi thiếu tiêu chí (rubric) — không chấm AI được.");
        }

        List<Map<String, Object>> criteriaPayload = normalizeCriteria(criteria);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("answer", answer.trim());
        body.put("question", questionText != null ? questionText : "");
        body.put("reference_answer", referenceAnswer.trim());
        body.put("criteria", criteriaPayload);
        body.put("mode", appProperties.getAi().getMode());
        body.put("include_debug", false);
        // Do not send question_id — force inline barem path (DB), not questions.json ids

        AppProperties.Ai ai = appProperties.getAi();
        String json;
        try {
            json = objectMapper.writeValueAsString(body);
        } catch (Exception ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Không tạo được JSON gửi AI: " + ex.getMessage());
        }

        log.info("AI evaluate request (question={}): {} chars, criteria={}",
                questionIdLabel, json.length(), criteriaPayload.size());

        HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofMillis(ai.getConnectTimeoutMs()))
                .build();

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(trimSlash(ai.getBaseUrl()) + "/v1/interview/evaluate"))
                .timeout(Duration.ofMillis(ai.getReadTimeoutMs()))
                .header("Content-Type", "application/json; charset=UTF-8")
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();

        try {
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            int code = response.statusCode();
            String respBody = response.body() != null ? response.body() : "";
            if (code < 200 || code >= 300) {
                log.error("AI evaluate HTTP {}: {}", code, respBody);
                throw new ApiException(HttpStatus.BAD_GATEWAY,
                        "AI chấm điểm lỗi (" + code + "): " + shorten(respBody, 400));
            }
            JsonNode root = objectMapper.readTree(respBody);
            if (root == null || root.get("predicted_score") == null || root.get("predicted_score").isNull()) {
                throw new ApiException(HttpStatus.BAD_GATEWAY, "AI trả về thiếu predicted_score.");
            }
            return parse(root);
        } catch (ApiException ex) {
            throw ex;
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Bị gián đoạn khi gọi AI.");
        } catch (Exception ex) {
            log.error("AI evaluate call failed", ex);
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Không kết nối được AI API (" + ai.getBaseUrl() + "). Chạy: uvicorn src.api:app --port 8000. Chi tiết: "
                            + ex.getMessage());
        }
    }

    private List<Map<String, Object>> normalizeCriteria(List<AiScoringDtos.CriterionIn> criteria) {
        double sum = 0;
        List<double[]> weights = new ArrayList<>();
        for (AiScoringDtos.CriterionIn c : criteria) {
            double w = Math.max(0, c.weight());
            weights.add(new double[]{w});
            sum += w;
        }
        if (sum <= 0) {
            sum = criteria.size();
            for (double[] w : weights) {
                w[0] = 1.0;
            }
        }

        List<Map<String, Object>> out = new ArrayList<>();
        for (int i = 0; i < criteria.size(); i++) {
            AiScoringDtos.CriterionIn c = criteria.get(i);
            double w = weights.get(i)[0] / sum; // 0..1, tổng = 1
            // clamp for pydantic Field(le=1)
            w = Math.min(1.0, Math.max(0.0, w));

            List<String> hints = new ArrayList<>();
            if (c.hints() != null) {
                for (String h : c.hints()) {
                    if (h != null && !h.isBlank()) {
                        hints.add(h.trim());
                    }
                }
            }

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("key", c.key() != null && !c.key().isBlank() ? c.key() : ("c" + i));
            item.put("label", c.label() != null && !c.label().isBlank() ? c.label() : ("Tiêu chí " + (i + 1)));
            item.put("weight", w);
            item.put("hints", hints);
            item.put("reference_answers", c.referenceAnswers() == null ? List.of(c.label()) : c.referenceAnswers());
            item.put("misconceptions", c.misconceptions() == null ? List.of() : c.misconceptions());
            out.add(item);
        }
        return out;
    }

    private AiScoringDtos.EvaluateResult parse(JsonNode root) {
        double score = Double.parseDouble(root.get("predicted_score").asString());
        String scale = text(root, "score_scale", "0-10");
        List<String> covered = arrayStrings(root.get("covered_points"));
        List<String> missing = arrayStrings(root.get("missing_points"));
        String comment = text(root, "comment", "");
        String modelVersion = text(root, "model_version", null);
        String mode = text(root, "mode", appProperties.getAi().getMode());
        if (!Double.isFinite(score) || score < 0 || score > 10)
            throw new ApiException(HttpStatus.BAD_GATEWAY, "AI score outside 0-10");
        if (!java.util.Set.of("fast", "bertscore", "finetune").contains(mode) || !mode.equals(appProperties.getAi().getMode()))
            throw new ApiException(HttpStatus.BAD_GATEWAY, "AI scoring mode does not match requested mode");
        Double precision = optionalNumber(root, "bertscore_precision");
        Double recall = optionalNumber(root, "bertscore_recall");
        Double f1 = optionalNumber(root, "bertscore_f1");
        if ("bertscore".equals(mode) && (precision == null || recall == null || f1 == null))
            throw new ApiException(HttpStatus.BAD_GATEWAY, "AI response has no BERTScore evidence");
        double coverage = root.path("coverage_score").asDouble();
        if (!Double.isFinite(coverage) || coverage < 0 || coverage > 1)
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Invalid criterion coverage");
        List<Map<String,Object>> details = root.path("criterion_results").isArray()
            ? objectMapper.convertValue(root.get("criterion_results"), List.class) : List.of();
        return new AiScoringDtos.EvaluateResult(score, scale, covered, missing, comment, modelVersion, mode,
            precision, recall, f1, coverage, details);
    }

    private static Double optionalNumber(JsonNode root, String field) {
        JsonNode value = root.get(field);
        if (value == null || value.isNull()) return null;
        if (!value.isNumber()) throw new ApiException(HttpStatus.BAD_GATEWAY, "Semantic metric must be numeric");
        double number = value.asDouble();
        if (!Double.isFinite(number) || number < 0 || number > 1)
            throw new ApiException(HttpStatus.BAD_GATEWAY, "Invalid semantic metric");
        return number;
    }

    private static String text(JsonNode root, String field, String fallback) {
        JsonNode n = root.get(field);
        if (n == null || n.isNull()) {
            return fallback;
        }
        String v = n.asString();
        return v == null || v.isBlank() || "null".equals(v) ? fallback : v;
    }

    private static List<String> arrayStrings(JsonNode node) {
        if (node == null || !node.isArray()) {
            return List.of();
        }
        List<String> out = new ArrayList<>();
        node.forEach(n -> {
            if (n != null && !n.isNull()) {
                out.add(n.asString());
            }
        });
        return out;
    }

    private static String trimSlash(String url) {
        if (url == null || url.isBlank()) {
            return "http://localhost:8000";
        }
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }

    private static String shorten(String s, int max) {
        if (s == null) {
            return "";
        }
        return s.length() <= max ? s : s.substring(0, max) + "…";
    }
}
