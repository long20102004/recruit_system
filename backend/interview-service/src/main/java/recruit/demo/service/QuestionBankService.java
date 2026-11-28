package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.QuestionBankDtos.*;
import recruit.demo.entity.EvaluationRubric;
import recruit.demo.entity.InterviewQuestion;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.EvaluationRubricRepository;
import recruit.demo.repository.InterviewQuestionRepository;
import recruit.demo.security.SecurityUtils;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.Set;

@Service
@RequiredArgsConstructor
public class QuestionBankService {
    private static final Set<String> LEVELS = Set.of("Intern", "Junior", "Middle", "Senior");
    private static final Set<String> TYPES = Set.of("Kiến thức", "Áp dụng", "Tình huống");
    private final InterviewQuestionRepository questions;
    private final EvaluationRubricRepository rubrics;

    @Transactional(readOnly = true)
    public PageResponse<Question> list(Pageable pageable) {
        return PageResponse.toPageResponse(questions.findByArchivedFalseOrderByIdDesc(pageable), this::toQuestion);
    }

    @Transactional
    public Question save(Integer id, Input input) {
        if (!LEVELS.contains(input.level()) || !TYPES.contains(input.type())
                || input.rubric().stream().mapToInt(Criterion::weight).sum() != 100) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Cấp độ, loại câu hỏi hoặc tổng trọng số rubric không hợp lệ");
        }
        if (id != null) {
            // Keep the original question and rubric for sessions already referencing this revision.
            var previous = requireEditable(id);
            previous.setActive(false);
            previous.setArchived(true);
        }
        var question = questions.save(InterviewQuestion.builder().createdById(SecurityUtils.currentUser().getId())
            .title(input.topic().trim()).topic(input.topic().trim()).skill(input.topic().trim())
            .questionText(input.questionText().trim()).referenceAnswer(input.referenceAnswer().trim())
            .seniority(input.level()).questionType(storedType(input.type())).source("admin")
            .active(false).reviewed(false).build());

        for (var item : input.rubric()) {
            rubrics.save(EvaluationRubric.builder().question(question).criterionName(item.name().trim())
                .criterionDescription(item.points()).referenceAnswers(parts(item.points(), "\\R"))
                .expectedKeywords(parts(item.keywords(), "[,;\n]"))
                .misconceptions(parts(item.misconceptions(), "\\R"))
                .weight(BigDecimal.valueOf(item.weight(), 2)).build());
        }
        return toQuestion(question);
    }

    @Transactional
    public Question changeState(Integer id, State state) {
        var question = requireEditable(id);
        if (state.approved() != null) {
            question.setReviewed(state.approved());
            question.setActive(state.approved());
        }
        if (state.enabled() != null) {
            if (state.enabled() && !question.isReviewed()) {
                throw new ApiException(HttpStatus.CONFLICT, "Duyệt câu hỏi trước khi bật");
            }
            question.setActive(state.enabled());
        }
        return toQuestion(question);
    }

    @Transactional
    public void archive(Integer id) {
        var question = requireEditable(id);
        question.setArchived(true);
        question.setActive(false);
    }

    private InterviewQuestion requireEditable(Integer id) {
        return questions.findEditable(id)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Question not found"));
    }

    private Question toQuestion(InterviewQuestion question) {
        var criteria = rubrics.findByQuestionId(question.getId());
        var total = criteria.stream().map(EvaluationRubric::getWeight).reduce(BigDecimal.ZERO, BigDecimal::add);
        var output = new ArrayList<Criterion>();
        int remaining = 100;
        for (int index = 0; index < criteria.size(); index++) {
            var item = criteria.get(index);
            int weight = index == criteria.size() - 1 ? remaining : total.signum() == 0 ? 0
                : Math.min(remaining, item.getWeight().multiply(BigDecimal.valueOf(100))
                    .divide(total, 0, RoundingMode.HALF_UP).intValue());
            remaining -= weight;
            String points = item.getReferenceAnswers() == null || item.getReferenceAnswers().isEmpty()
                ? Objects.toString(item.getCriterionDescription(), "") : String.join("\n", item.getReferenceAnswers());
            output.add(new Criterion(item.getCriterionName(), weight, points,
                join(item.getExpectedKeywords(), ", "), join(item.getMisconceptions(), "\n")));
        }
        String type = switch (Objects.toString(question.getQuestionType(), "")) {
            case "APPLICATION" -> "Áp dụng";
            case "SCENARIO" -> "Tình huống";
            default -> "Kiến thức";
        };
        return new Question(question.getId(), question.getQuestionText(),
            Objects.toString(question.getTopic(), Objects.toString(question.getSkill(), "Khác")),
            Objects.toString(question.getSeniority(), "Junior"), type,
            Objects.toString(question.getReferenceAnswer(), ""), output, question.isReviewed(), question.isActive());
    }

    private static String storedType(String title) {
        return switch (title) {
            case "Áp dụng" -> "APPLICATION";
            case "Tình huống" -> "SCENARIO";
            default -> "KNOWLEDGE";
        };
    }

    private static List<String> parts(String value, String separator) {
        return value == null ? List.of() : Arrays.stream(value.split(separator))
            .map(String::trim).filter(part -> !part.isEmpty()).toList();
    }

    private static String join(List<String> values, String separator) {
        return values == null ? "" : String.join(separator, values);
    }
}
