package recruit.demo.controller;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.ServiceDtos.QuestionCount;
import recruit.demo.repository.InterviewQuestionRepository;
@RestController
@RequiredArgsConstructor
public class InternalInterviewController {
    private final InterviewQuestionRepository questions;
    @GetMapping("/internal/interviews/question-count")
    public QuestionCount count() { return new QuestionCount(questions.countByActiveTrue()); }
}
