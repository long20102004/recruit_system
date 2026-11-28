package recruit.demo.service.impl;
import recruit.demo.service.*;
import org.springframework.stereotype.Service;
import recruit.demo.dto.ServiceDtos.InterviewContext;
import recruit.demo.entity.InterviewQuestion;
import recruit.demo.kb.SkillGraph;
import java.util.*;
@Service
public class QuestionSelectionServiceImpl implements QuestionSelectionService {
    private final SkillGraph graph = SkillGraph.shared();
    private String normalize(String text) {
        String s = Objects.toString(text, "").toLowerCase(Locale.ROOT).replaceAll("[^\\p{L}\\p{N}]", "");
        return switch(s) { case "spring", "springboot" -> "springboot";
            case "mysql", "postgresql", "sqlserver" -> "sql";
            case "rest", "restful", "restapi", "http" -> "restapi";
            case "reactjs", "react" -> "react";
            case "nlp", "pytorch", "tensorflow", "machinelearning", "bert" -> "machinelearning";
            default -> s; };
    }
    private int level(String value) {
        return switch(Objects.toString(value, "Junior").toLowerCase(Locale.ROOT)) {
            case "intern", "fresher", "easy" -> 0;
            case "middle", "hard" -> 2;
            case "senior", "lead" -> 3;
            default -> 1;
        };
    }
    private Set<String> skills(List<String> values) {
        Set<String> result = new HashSet<>(); if (values != null) values.forEach(v -> result.add(normalize(v))); return result;
    }
    public List<InterviewQuestion> select(List<InterviewQuestion> pool, InterviewContext context,
            Set<Integer> recent, int count) {
        Set<String> required = skills(context.requiredSkills()), candidate = skills(context.candidateSkills());
        required.addAll(skills(graph.mentioned(context.jobTitle())));
        int target = level(context.seniority());
        var eligible = pool.stream().filter(InterviewQuestion::isActive)
            .filter(q -> Set.of("synthetic-ai-v2", "admin", "senior-bank").contains(Objects.toString(q.getSource(), "")))
            .filter(q -> level(q.getSeniority()) <= target + 1)
            .sorted(Comparator.<InterviewQuestion>comparingInt(q -> {
                String skill = normalize(q.getSkill());
                int match = required.contains(skill) ? 40 : candidate.contains(skill) ? 20 : graphScore(required, candidate, skill);
                return match - 3 * Math.abs(level(q.getSeniority()) - target) - (recent.contains(q.getId()) ? 12 : 0);
            }).reversed().thenComparing(InterviewQuestion::getId)).toList();
        List<InterviewQuestion> result = new ArrayList<>(); Map<String,Integer> bySkill = new HashMap<>();
        Map<String,Integer> byType = new HashMap<>();
        for (var q : eligible) {
            String skill = normalize(q.getSkill());
            if (bySkill.getOrDefault(skill,0) >= 2 || byType.getOrDefault(q.getQuestionType(),0) >= Math.max(2, (count+1)/2)) continue;
            result.add(q); bySkill.merge(skill,1,Integer::sum); byType.merge(q.getQuestionType(),1,Integer::sum);
            if (result.size()==count) return result;
        }
        // Small specialised pools still produce a full session; all questions stay distinct and level-bounded.
        for (var q : eligible) if (!result.contains(q) && result.size()<count) result.add(q);
        return result;
    }

    private int graphScore(Set<String> required, Set<String> candidate, String skill) {
        int best = Set.of("security", "git", "restapi", "sql").contains(skill) ? 8 : 0;
        for (String known : required) {
            int distance = graph.distance(known, skill);
            if (distance == 1) best = Math.max(best, 16);
            else if (distance == 2) best = Math.max(best, 10);
        }
        for (String known : candidate) {
            int distance = graph.distance(known, skill);
            if (distance == 1) best = Math.max(best, 12);
            else if (distance == 2) best = Math.max(best, 8);
        }
        return best;
    }
}
