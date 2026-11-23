package recruit.demo.service;
import org.junit.jupiter.api.Test;
import recruit.demo.dto.ServiceDtos.InterviewContext;
import recruit.demo.entity.InterviewQuestion;
import recruit.demo.kb.SkillGraph;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class QuestionSelectionServiceTest {
    private InterviewQuestion q(int id,String skill,String level) {
        return InterviewQuestion.builder().id(id).skill(skill).seniority(level).questionType("APPLICATION")
            .source("synthetic-ai-v2").active(true).build();
    }
    private InterviewContext context(String level) {
        return new InterviewContext(1,10,20,"Java Developer",null,List.of("Spring Boot"),List.of("Java"),level,30);
    }
    @Test void prioritisesRequiredSkillsAndNormalisesAliases() {
        var pool=List.of(q(1,"React","Junior"),q(2,"Spring Boot","Junior"),q(3,"Java","Junior"));
        assertEquals(2,new QuestionSelectionService().select(pool,context("Junior"),Set.of(),1).get(0).getId());
    }
    @Test void avoidsRecentQuestionsWhenComparableAlternativesExist() {
        var pool=List.of(q(1,"Spring Boot","Junior"),q(2,"Spring Boot","Junior"));
        assertEquals(2,new QuestionSelectionService().select(pool,context("Junior"),Set.of(1),1).get(0).getId());
    }
    @Test void springBootPullsTheJavaQuestionAheadOfAnUnrelatedSkill() {
        assertEquals(1, SkillGraph.shared().distance("Spring Boot", "Java"));
        var pool = List.of(q(1, "React", "Junior"), q(2, "Java", "Junior"));
        var context = new InterviewContext(1, 10, 20, "Backend", null, List.of("Spring Boot"), List.of(), "Junior", 30);
        assertEquals(2, new QuestionSelectionService().select(pool, context, Set.of(), 1).get(0).getId());
    }
    @Test void excludesInactiveAndTooAdvancedQuestionsAndNeverDuplicates() {
        var inactive=q(3,"Spring Boot","Junior");inactive.setActive(false);
        var result=new QuestionSelectionService().select(List.of(q(1,"Java","Intern"),q(2,"Java","Middle"),inactive),context("Intern"),Set.of(),6);
        assertEquals(List.of(1),result.stream().map(InterviewQuestion::getId).toList());
    }
}
