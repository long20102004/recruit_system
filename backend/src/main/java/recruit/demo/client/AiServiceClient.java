package recruit.demo.client;

import recruit.demo.dto.AiCvRequest;
import recruit.demo.dto.AiCvResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

//@FeignClient(name = "ai-service", url = "${ai.service.url:https://bennett-scheme-acts-glass.trycloudflare.com}")
@FeignClient(name = "ai-service", url = "${ai.service.url:http://localhost:8000}")

public interface AiServiceClient {

    @PostMapping(value = "/api/v1/extract-cv", produces = "application/json")
    AiCvResponse extractCv(@RequestBody AiCvRequest request);
}
