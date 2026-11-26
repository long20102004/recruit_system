package recruit.demo.controller;

import org.springframework.security.access.prepost.PreAuthorize;
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

    @PreAuthorize("hasAuthority('question:read')")
    public List<InterviewDtos.QuestionResponse> listQuestions() {
        return interviewService.listQuestions();
    }

    @PostMapping("/sessions")

    @PreAuthorize("hasAuthority('interview:practice')")
    public InterviewDtos.SessionResponse createSession(@RequestBody(required = false) InterviewDtos.CreateSessionRequest request) {
        return interviewService.createSession(request != null ? request : new InterviewDtos.CreateSessionRequest(null, null, null, null));
    }

    @GetMapping("/sessions/mine")

    @PreAuthorize("hasAuthority('interview:practice')")
    public List<InterviewDtos.SessionResponse> mine() { return interviewService.mySessions(); }

    @GetMapping("/sessions/{id}/summary")

    @PreAuthorize("hasAnyAuthority('interview:practice', 'interview:read-result', 'interview:read-all')")
    public InterviewDtos.SessionSummary summary(@PathVariable Integer id) { return interviewService.summary(id); }

    @GetMapping("/sessions/{id}")

    @PreAuthorize("hasAnyAuthority('interview:practice', 'interview:read-result', 'interview:read-all')")
    public InterviewDtos.SessionResponse getSession(@PathVariable Integer id) {
        return interviewService.getSession(id);
    }

    @PostMapping("/sessions/{id}/responses")

    @PreAuthorize("hasAuthority('interview:practice')")
    public InterviewDtos.EvaluationResponse submitResponse(@PathVariable Integer id,
                                                           @Valid @RequestBody InterviewDtos.SubmitResponseRequest request) {
        return interviewService.submitAndEvaluate(id, request);
    }
}
