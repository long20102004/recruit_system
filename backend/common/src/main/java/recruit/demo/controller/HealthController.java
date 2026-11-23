package recruit.demo.controller;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;
@RestController
public class HealthController {
    private final String name;
    public HealthController(@Value("${spring.application.name}") String name) { this.name = name; }
    @GetMapping("/health")
    public Map<String, String> health() { return Map.of("status", "ok", "service", name); }
}
