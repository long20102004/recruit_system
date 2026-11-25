package recruit.demo.service;
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
    private InterviewService service() { return new InterviewService(questions,rubrics,sessions,items,responses,evaluations,ai,new QuestionSelectionService(),http); }
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
    @Test void duplicateExplicitQuestionsAreRejected() {
        authenticate();try {
            var context=new ServiceDtos.InterviewContext(1,10,null,null,null,List.of(),List.of(),"Junior",null);
            when(http.interviewContext(anyInt(),any(),any())).thenReturn(context);
            assertEquals(400,assertThrows(ApiException.class,()->service().createSession(new InterviewDtos.CreateSessionRequest(null,null,List.of(2,2),null))).getStatus().value());
            verify(sessions,never()).save(any());
        } finally { SecurityContextHolder.clearContext(); }
    }
}
