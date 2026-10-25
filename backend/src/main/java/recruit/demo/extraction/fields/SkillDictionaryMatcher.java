package recruit.demo.extraction.fields;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Từ điển công nghệ với alias, khớp cụm dài nhất trước (Giai đoạn 3).
 *
 * <p>Ví dụ {@code sklearn} → {@code Scikit-learn}. Khớp dùng word-boundary
 * case-insensitive nên "Java" không khớp nhầm bên trong "JavaScript".
 * Trả về tên chuẩn theo thứ tự xuất hiện, khử trùng.
 */
public final class SkillDictionaryMatcher {

    private final List<Entry> entries = new ArrayList<>();
    private final Map<String, String> aliasToCanonical = new LinkedHashMap<>();

    private record Entry(String canonical, Pattern pattern) {
    }

    public SkillDictionaryMatcher() {
        // Ngôn ngữ
        add("Java", "java", "\\bjava\\b(?!script)");
        add("JavaScript", "javascript", "js", "ecmascript");
        add("TypeScript", "typescript", "ts");
        add("Python", "python", "py");
        add("C#", "c#", "csharp", "c sharp");
        add("C++", "c\\+\\+");
        add("C", "\\bc\\b(?!\\+|#)");
        add("PHP", "php");
        add("Go", "\\bgo\\b", "golang");
        add("Kotlin", "kotlin");
        add("Swift", "swift");
        add("Dart", "dart");
        add("SQL", "sql");
        add("HTML", "html", "html5");
        add("CSS", "css", "css3", "scss", "sass");
        // Backend frameworks
        add("Spring Boot", "spring boot", "springboot");
        add("Spring MVC", "spring mvc");
        add("Spring Security", "spring security");
        add("Spring Cloud", "spring cloud");
        add("Hibernate", "hibernate");
        add("JPA", "jpa");
        add("FastAPI", "fastapi", "fast api");
        add("Django", "django");
        add("Flask", "flask");
        add("Node.js", "node\\.?js", "nodejs", "node");
        add("Express.js", "express\\.?js?", "expressjs");
        add("NestJS", "nestjs", "nest\\.js");
        add("Laravel", "laravel");
        add(".NET", "\\.net", "dotnet", "asp\\.net");
        // Frontend
        add("React", "reactjs", "react\\.js", "\\breact\\b(?! native)");
        add("React Native", "react native");
        add("Next.js", "next\\.?js", "nextjs");
        add("Vue.js", "vue\\.?js", "vuejs", "\\bvue\\b");
        add("Angular", "angular", "angularjs");
        add("Flutter", "flutter");
        add("Redux", "redux");
        add("Tailwind CSS", "tailwind");
        add("Bootstrap", "bootstrap");
        add("jQuery", "jquery");
        // Data / AI
        add("PyTorch", "pytorch", "torch");
        add("TensorFlow", "tensorflow", "tf");
        add("Scikit-learn", "scikit-learn", "sklearn", "scikit learn");
        add("Pandas", "pandas");
        add("NumPy", "numpy");
        add("OpenCV", "opencv", "open cv");
        add("YOLO", "yolo");
        add("LangChain", "langchain", "lang chain");
        add("LangGraph", "langgraph", "lang graph");
        add("Spark", "apache spark", "\\bspark\\b");
        add("Kafka", "kafka");
        add("Airflow", "airflow");
        add("Power BI", "power ?bi", "powerbi");
        add("Tableau", "tableau");
        add("Elasticsearch", "elasticsearch", "elastic search");
        // Database
        add("MySQL", "mysql", "my sql");
        add("PostgreSQL", "postgresql", "postgres");
        add("MongoDB", "mongodb", "mongo db", "mongo");
        add("Redis", "redis");
        add("SQL Server", "sql server");
        add("Oracle", "oracle db", "\\boracle\\b");
        add("SQLite", "sqlite");
        add("Firebase", "firebase");
        // DevOps / Cloud
        add("Docker", "docker");
        add("Kubernetes", "kubernetes", "k8s");
        add("Jenkins", "jenkins");
        add("GitLab CI/CD", "gitlab ci");
        add("GitHub Actions", "github actions");
        add("Terraform", "terraform");
        add("Ansible", "ansible");
        add("Prometheus", "prometheus");
        add("Grafana", "grafana");
        add("Nginx", "nginx");
        add("AWS", "\\baws\\b", "amazon web services", "ec2", "s3");
        add("GCP", "\\bgcp\\b", "google cloud");
        add("Azure", "azure");
        add("Linux", "linux", "ubuntu");
        add("Git", "\\bgit\\b(?!hub|lab)", "github", "gitlab");
        add("Postman", "postman");
        add("Swagger", "swagger", "openapi");
        add("RabbitMQ", "rabbitmq", "rabbit mq");
        add("gRPC", "grpc", "g-rpc");
        add("GraphQL", "graphql", "graph ql");
        add("JWT", "jwt");
        add("OAuth2", "oauth2?", "oauth");
        add("Gradle", "gradle");
        add("Maven", "maven");
        add("Jira", "jira");
        add("Figma", "figma");
        add("Selenium", "selenium");
        add("Cypress", "cypress");
        add("Playwright", "playwright");
        add("JMeter", "jmeter");
        sortByLengthDesc();
    }

    private void add(String canonical, String... aliases) {
        for (String a : aliases) {
            aliasToCanonical.put(a, canonical);
        }
    }

    private static final int FLAGS =
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE | Pattern.UNICODE_CHARACTER_CLASS;

    private void sortByLengthDesc() {
        List<Map.Entry<String, String>> sorted = new ArrayList<>(aliasToCanonical.entrySet());
        sorted.sort((a, b) -> Integer.compare(b.getKey().length(), a.getKey().length()));
        for (Map.Entry<String, String> e : sorted) {
            entries.add(new Entry(e.getValue(), Pattern.compile(e.getKey(), FLAGS)));
        }
    }

    /**
     * Tìm công nghệ trong text, giới hạn trong phạm vi đã cho (block/job/project).
     * Không bao giờ lấy ngoài phạm vi truyền vào (chống sao chép kỹ năng chung).
     * Kết quả theo thứ tự xuất hiện trong text, khử trùng.
     */
    public List<String> match(String scopedText) {
        List<String> out = new ArrayList<>();
        if (scopedText == null || scopedText.isBlank()) {
            return out;
        }
        boolean[] used = new boolean[scopedText.length()];
        Map<String, Integer> firstPos = new java.util.LinkedHashMap<>();
        for (Entry e : entries) {
            Matcher m = e.pattern().matcher(scopedText);
            while (m.find()) {
                int s = m.start();
                int en = m.end();
                boolean overlap = false;
                for (int i = s; i < en; i++) {
                    if (used[i]) {
                        overlap = true;
                        break;
                    }
                }
                if (overlap) {
                    continue;
                }
                for (int i = s; i < en; i++) {
                    used[i] = true;
                }
                firstPos.putIfAbsent(e.canonical(), s);
            }
        }
        List<Map.Entry<String, Integer>> ordered = new ArrayList<>(firstPos.entrySet());
        ordered.sort(Map.Entry.comparingByValue());
        for (Map.Entry<String, Integer> e : ordered) {
            out.add(e.getKey());
        }
        return out;
    }
}
