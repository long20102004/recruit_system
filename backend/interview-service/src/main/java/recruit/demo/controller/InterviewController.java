package recruit.demo.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import recruit.demo.dto.BaseResponse;
import recruit.demo.dto.InterviewDtos;
import recruit.demo.dto.PageResponse;
import recruit.demo.dto.Paging;
import recruit.demo.service.InterviewService;

@RestController
@RequestMapping("/api/interviews")
@RequiredArgsConstructor
public class InterviewController {

    private final InterviewService interviewService;

    @GetMapping("/questions")
    @PreAuthorize("hasAuthority('question:read')")
    public BaseResponse<PageResponse<InterviewDtos.QuestionResponse>> listQuestions(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(interviewService.listQuestions(Paging.of(page, size)));
    }

    @PostMapping("/sessions")
    @PreAuthorize("hasAuthority('interview:practice')")
    public InterviewDtos.SessionResponse createSession(@RequestBody(required = false) InterviewDtos.CreateSessionRequest request) {
        return interviewService.createSession(request != null ? request : new InterviewDtos.CreateSessionRequest(null, null, null, null));
    }

    @GetMapping("/sessions/mine")
    @PreAuthorize("hasAuthority('interview:practice')")
    public BaseResponse<PageResponse<InterviewDtos.SessionResponse>> mine(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return BaseResponse.success(interviewService.mySessions(Paging.of(page, size)));
    }

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
