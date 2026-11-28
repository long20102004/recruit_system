package recruit.demo.service.impl;
import recruit.demo.service.*;
import recruit.demo.enums.Role;
import recruit.demo.enums.SessionStatus;
import recruit.demo.enums.UserStatus;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.entity.*;
import recruit.demo.repository.*;
import recruit.demo.dto.*;
import recruit.demo.client.RecruitmentServiceClient;
import recruit.demo.exception.ApiException;
import recruit.demo.security.UserPrincipal;
import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class InterviewLifecycleTest {
    private final InterviewQuestionRepository questions=mock(InterviewQuestionRepository.class);
    private final EvaluationRubricRepository rubrics=mock(EvaluationRubricRepository.class);
    private final InterviewSessionRepository sessions=mock(InterviewSessionRepository.class);
    private final InterviewSessionQuestionRepository items=mock(InterviewSessionQuestionRepository.class);
    private final InterviewResponseRepository responses=mock(InterviewResponseRepository.class);
    private final EvaluationResultRepository evaluations=mock(EvaluationResultRepository.class);
    private final AiScoringClient ai=mock(AiScoringClient.class);
    private final RecruitmentServiceClient http=mock(RecruitmentServiceClient.class);
    private InterviewService service() { return new InterviewServiceImpl(questions,rubrics,sessions,items,responses,evaluations,ai,new QuestionSelectionServiceImpl(),http); }
    private void authenticate() {
        var user=new UserPrincipal(10,"test@example.com","","Test",Role.CANDIDATE,UserStatus.ACTIVE);
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(user,null,user.getAuthorities()));
    }
    @Test void lastGradedAnswerCompletesSessionAndPersistsSemanticEvidence() {
        authenticate();
        try {
            var session=InterviewSession.builder().id(1).candidateUserId(10).status(SessionStatus.CREATED).build();
            var question=InterviewQuestion.builder().id(2).referenceAnswer("Reference").build();
            var item=InterviewSessionQuestion.builder().id(3).session(session).question(question).maxScore(BigDecimal.TEN).build();
            when(sessions.findForUpdate(1)).thenReturn(Optional.of(session));
            when(sessions.findById(1)).thenReturn(Optional.of(session));
            when(items.findBySessionIdAndQuestionId(1,2)).thenReturn(Optional.of(item));
            when(items.findBySessionIdOrdered(1)).thenReturn(List.of(item));
            when(responses.findBySessionQuestionId(3)).thenReturn(Optional.empty());
            when(responses.save(any())).thenAnswer(call -> { InterviewResponse r=call.getArgument(0);r.setId(4);when(responses.findBySessionQuestionId(3)).thenReturn(Optional.of(r));return r; });
            var rubric=EvaluationRubric.builder().id(5).criterionName("Criterion").weight(BigDecimal.ONE).referenceAnswers(List.of("Reference")).build();
            when(rubrics.findByQuestionId(2)).thenReturn(List.of(rubric));
            var result=new AiScoringDtos.EvaluateResult(8.25,"0-10",List.of("Covered"),List.of(),"Feedback","module3-bertscore-rubric-v2","bertscore",.9,.8,.85,.75,List.of());
            when(ai.evaluate(anyString(),any(),any(),anyList(),anyString())).thenReturn(result);
            var saved=new AtomicReference<EvaluationResult>();
            when(evaluations.findByResponseId(4)).thenAnswer(call -> Optional.ofNullable(saved.get()));
            when(evaluations.save(any())).thenAnswer(call -> {EvaluationResult e=call.getArgument(0);e.setId(6);saved.set(e);return e;});
            var dto=service().submitAndEvaluate(1,new InterviewDtos.SubmitResponseRequest(2,"My response"));
            assertEquals(SessionStatus.COMPLETED,session.getStatus());assertNotNull(session.getCompletedAt());
            assertEquals(new BigDecimal("0.8500"),dto.bertscoreF1());
            assertEquals("bertscore",dto.scoringMode());
            assertEquals("BERTSCORE_RUBRIC",saved.get().getEvaluationMethod());
            assertNull(saved.get().getCorrectnessScore());
            assertEquals(1,service().getSession(1).currentIndex());
            assertEquals(new BigDecimal("8.25"),service().summary(1).averageScore());
            assertEquals(409,assertThrows(ApiException.class,()->service().submitAndEvaluate(1,new InterviewDtos.SubmitResponseRequest(2,"Again"))).getStatus().value());
        } finally { SecurityContextHolder.clearContext(); }
    }
    @Test void candidateCannotSubmitToAnotherCandidatesSession() {
        authenticate();try {
            when(sessions.findForUpdate(1)).thenReturn(Optional.of(InterviewSession.builder().id(1).candidateUserId(99).build()));
            assertEquals(403,assertThrows(ApiException.class,()->service().submitAndEvaluate(1,new InterviewDtos.SubmitResponseRequest(2,"Answer"))).getStatus().value());
            verifyNoInteractions(ai);
        } finally { SecurityContextHolder.clearContext(); }
    }
    @Test void recruiterLosesAccessWhenCompanyMembershipIsRemoved() {
        var recruiter = new UserPrincipal(20, "recruiter@example.com", "", "Recruiter",
                Role.RECRUITER, UserStatus.ACTIVE, null, Set.of("interview:read-result"));
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(recruiter, null, recruiter.getAuthorities()));
        try {
            var session = InterviewSession.builder().id(1).candidateUserId(10)
                    .recruiterUserId(20).applicationId(5).jobId(7).status(SessionStatus.COMPLETED).build();
            when(sessions.findById(1)).thenReturn(Optional.of(session));
            when(http.canReadInterview(20, 7)).thenReturn(true, false);
            assertEquals(1, service().summary(1).sessionId());
            assertEquals(403, assertThrows(ApiException.class, () -> service().summary(1)).getStatus().value());
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test void latestResultUsesOnlyCompletedSessionsLinkedToTheApplication() {
        var session = InterviewSession.builder().id(1).applicationId(5).jobId(7).candidateUserId(10)
                .status(SessionStatus.COMPLETED).build();
        when(sessions.findFirstByApplicationIdAndJobIdAndCandidateUserIdAndStatusOrderByCompletedAtDescIdDesc(
                5, 7, 10, SessionStatus.COMPLETED)).thenReturn(Optional.of(session));

        assertEquals(1, service().latestResult(5, 7, 10).sessionId());
        assertNull(service().latestResult(6, 7, 10));
        verifyNoInteractions(ai);
    }

    @Test void candidateQueuesAnswerWithoutCallingScoringAndDuplicateSubmissionKeepsOriginal() {
        authenticate();
        try {
            var session = InterviewSession.builder().id(1).candidateUserId(10).build();
            var question = InterviewQuestion.builder().id(2).build();
            var item = InterviewSessionQuestion.builder().id(3).session(session).question(question).build();
            when(sessions.findForUpdate(1)).thenReturn(Optional.of(session));
            when(items.findBySessionIdAndQuestionId(1, 2)).thenReturn(Optional.of(item));
            var queued = new AtomicReference<InterviewResponse>();
            when(responses.findBySessionQuestionId(3)).thenAnswer(call -> Optional.ofNullable(queued.get()));
            when(responses.save(any())).thenAnswer(call -> {
                InterviewResponse answer = call.getArgument(0);
                answer.setId(4);
                queued.set(answer);
                return answer;
            });

            assertEquals("PENDING", service().queueEvaluation(1,
                new InterviewDtos.SubmitResponseRequest(2, "First answer")).status());
            assertEquals("PENDING", service().queueEvaluation(1,
                new InterviewDtos.SubmitResponseRequest(2, "Duplicate request")).status());
            assertEquals("First answer", queued.get().getAnswerText());
            verify(responses).save(any());
            verifyNoInteractions(ai);
        } finally {
            SecurityContextHolder.clearContext();
        }
    }

    @Test void duplicateExplicitQuestionsAreRejected() {
        authenticate();try {
            var context=new ServiceDtos.InterviewContext(1,10,null,null,null,List.of(),List.of(),"Junior",null);
            when(http.interviewContext(anyInt(),any(),any())).thenReturn(context);
            assertEquals(400,assertThrows(ApiException.class,()->service().createSession(new InterviewDtos.CreateSessionRequest(null,null,List.of(2,2),null))).getStatus().value());
            verify(sessions,never()).save(any());
        } finally { SecurityContextHolder.clearContext(); }
    }
}
