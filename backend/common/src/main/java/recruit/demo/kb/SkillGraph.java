package recruit.demo.kb;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

import java.io.InputStream;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/** Shared skill graph exported from the CV knowledge base. */
public final class SkillGraph {
    private static final SkillGraph SHARED = load();
    private static final Set<String> BROAD_TYPES = Set.of(
            "frontendframework", "backendframework", "webframework", "api", "database",
            "cloudcomputing", "datascience", "shellscripting");
    private final Map<String, String> aliasToId;
    private final Map<String, String> names;
    private final Map<String, List<String>> adjacent;

    private SkillGraph(Map<String, String> aliasToId, Map<String, String> names, Map<String, List<String>> adjacent) {
        this.aliasToId = aliasToId;
        this.names = names;
        this.adjacent = adjacent;
    }

    public static SkillGraph shared() {
        return SHARED;
    }

    public int distance(String left, String right) {
        String from = resolve(left);
        String to = resolve(right);
        if (from.isBlank() || to.isBlank()) {
            return -1;
        }
        if (from.equals(to)) {
            return 0;
        }
        Set<String> seen = new HashSet<>();
        List<String> wave = List.of(from);
        seen.add(from);
        for (int depth = 1; depth <= 3 && !wave.isEmpty(); depth++) {
            List<String> next = new ArrayList<>();
            for (String node : wave) {
                for (String neighbor : adjacent.getOrDefault(node, List.of())) {
                    if (!seen.add(neighbor)) {
                        continue;
                    }
                    if (neighbor.equals(to)) {
                        return depth;
                    }
                    next.add(neighbor);
                }
            }
            wave = next;
        }
        return -1;
    }

    public List<String> mentioned(String text) {
        if (text == null || text.isBlank()) {
            return List.of();
        }
        String haystack = " " + text.toLowerCase(Locale.ROOT) + " ";
        List<String> found = new ArrayList<>();
        for (Map.Entry<String, String> node : names.entrySet()) {
            String name = node.getValue();
            if (name.length() < 3 || BROAD_TYPES.contains(node.getKey())) {
                continue;
            }
            if (containsPhrase(haystack, name.toLowerCase(Locale.ROOT))) {
                found.add(name);
            }
        }
        return found;
    }

    private boolean containsPhrase(String haystack, String needle) {
        return Pattern.compile("(?<![\\p{L}\\p{N}])" + Pattern.quote(needle) + "(?![\\p{L}\\p{N}])")
                .matcher(haystack).find();
    }

    private String resolve(String text) {
        String id = key(text);
        return aliasToId.getOrDefault(id, names.containsKey(id) ? id : "");
    }

    static String key(String text) {
        String normalized = Normalizer.normalize(text == null ? "" : text, Normalizer.Form.NFD);
        StringBuilder builder = new StringBuilder();
        for (int index = 0; index < normalized.length(); index++) {
            char character = normalized.charAt(index);
            if (Character.getType(character) == Character.NON_SPACING_MARK) {
                continue;
            }
            if (character == 'đ' || character == 'Đ') {
                character = 'd';
            }
            if (Character.isLetterOrDigit(character)) {
                builder.append(Character.toLowerCase(character));
            }
        }
        return builder.toString();
    }

    private static SkillGraph load() {
        try (InputStream input = SkillGraph.class.getResourceAsStream("/kb/skill_graph.json")) {
            if (input == null) {
                return new SkillGraph(Map.of(), Map.of(), Map.of());
            }
            JsonNode root = new ObjectMapper().readTree(input);
            Map<String, String> names = new LinkedHashMap<>();
            for (JsonNode node : root.path("nodes")) {
                names.put(node.path("id").asString(), node.path("name").asString());
            }
            Map<String, String> aliases = new HashMap<>();
            for (JsonNode alias : root.path("aliases")) {
                aliases.put(alias.path("from").asString(), alias.path("to").asString());
            }
            Map<String, List<String>> adjacent = new HashMap<>();
            for (JsonNode edge : root.path("edges")) {
                link(adjacent, edge.path("from").asString(), edge.path("to").asString());
                link(adjacent, edge.path("to").asString(), edge.path("from").asString());
            }
            return new SkillGraph(aliases, names, adjacent);
        } catch (Exception ex) {
            return new SkillGraph(Map.of(), Map.of(), Map.of());
        }
    }

    private static void link(Map<String, List<String>> adjacent, String from, String to) {
        if (from.isBlank() || to.isBlank() || from.equals(to)) {
            return;
        }
        adjacent.computeIfAbsent(from, ignored -> new ArrayList<>()).add(to);
    }
}
