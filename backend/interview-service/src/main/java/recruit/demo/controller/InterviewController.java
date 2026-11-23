package recruit.demo.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.InterviewDtos;
import recruit.demo.service.InterviewService;

import java.util.List;

@RestController
@RequestMapping("/api/interviews")
@RequiredArgsConstructor
public class InterviewController {

    private final InterviewService interviewService;

    @GetMapping("/questions")
    public List<InterviewDtos.QuestionResponse> listQuestions() {
        return interviewService.listQuestions();
    }

    @PostMapping("/sessions")
    public InterviewDtos.SessionResponse createSession(@RequestBody(required = false) InterviewDtos.CreateSessionRequest request) {
        return interviewService.createSession(request != null ? request : new InterviewDtos.CreateSessionRequest(null, null, null, null));
    }

    @GetMapping("/sessions/mine")
    public List<InterviewDtos.SessionResponse> mine() { return interviewService.mySessions(); }

    @GetMapping("/sessions/{id}/summary")
    public InterviewDtos.SessionSummary summary(@PathVariable Integer id) { return interviewService.summary(id); }

    @GetMapping("/sessions/{id}")
    public InterviewDtos.SessionResponse getSession(@PathVariable Integer id) {
        return interviewService.getSession(id);
    }

    @PostMapping("/sessions/{id}/responses")
    public InterviewDtos.EvaluationResponse submitResponse(@PathVariable Integer id,
                                                           @Valid @RequestBody InterviewDtos.SubmitResponseRequest request) {
        return interviewService.submitAndEvaluate(id, request);
    }
}
