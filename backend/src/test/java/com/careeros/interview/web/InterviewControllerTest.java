package com.careeros.interview.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.interview.entity.InterviewEvaluation;
import com.careeros.interview.entity.InterviewSession;
import com.careeros.interview.entity.InterviewTurn;
import com.careeros.interview.repository.InterviewDigestRepository;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.interview.repository.InterviewTurnRepository;
import com.careeros.interview.service.InterviewService;
import com.careeros.job.entity.Job;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.support.TestTransactions;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The mock-interview surface: create, read, rename, delete, and the three AI verbs —
 * opening, answer, finalize. DomainApiIT covers create + detail against the fake client;
 * nothing stated the state machine (opening before answer, answer before finalize), the
 * follow-up turn's rules (asked only when a question exists and the action is not "finish"),
 * or the foreign-session scoping that keeps another user's interview from being answered.
 *
 * The service runs for real here (mocked repositories + mocked AI client), so the turn
 * sequencing, the 400 guards, the finalize upsert and the difficulty adjustment are all
 * under test — the parts a fake client in an IT would silently satisfy.
 */
class InterviewControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID SESSION = UUID.fromString("33333333-3333-4333-8333-333333333333");
    private static final UUID JOB = UUID.fromString("55555555-5555-5555-5555-555555555555");

    private InterviewSessionRepository sessions;
    private InterviewTurnRepository turns;
    private InterviewEvaluationRepository evaluations;
    private AiServiceClient ai;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        sessions = mock(InterviewSessionRepository.class);
        turns = mock(InterviewTurnRepository.class);
        evaluations = mock(InterviewEvaluationRepository.class);
        JobRepository jobs = mock(JobRepository.class);
        CompanyRepository companies = mock(CompanyRepository.class);
        InterviewDigestRepository digests = mock(InterviewDigestRepository.class);
        when(digests.forSessions(any())).thenReturn(Map.of());
        ai = mock(AiServiceClient.class);
        when(sessions.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(turns.save(any())).thenAnswer(inv -> inv.getArgument(0));
        when(evaluations.save(any())).thenAnswer(inv -> inv.getArgument(0));

        InterviewService service = new InterviewService(sessions, turns, evaluations, jobs,
                companies, digests, ai, TestTransactions.executing());
        mvc = MockMvcBuilders.standaloneSetup(new InterviewController(service))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        as(ALICE);
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    private static void as(UUID id) {
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(id, "ada@example.invalid", "user"), null, List.of()));
    }

    private static void set(Object target, String field, Object value) {
        try {
            java.lang.reflect.Field f = target.getClass().getDeclaredField(field);
            f.setAccessible(true);
            f.set(target, value);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("cannot set " + field, e);
        }
    }

    private static InterviewSession session(String status) {
        InterviewSession s = new InterviewSession();
        set(s, "id", SESSION);
        s.setUserId(ALICE);
        s.setStatus(status);
        return s;
    }

    private void givenOwned(String status) {
        when(sessions.findByIdAndUserId(SESSION, ALICE)).thenReturn(Optional.of(session(status)));
    }

    private static InterviewTurn turn(int seq, String role, String content) {
        InterviewTurn t = new InterviewTurn();
        set(t, "id", UUID.randomUUID());
        t.setSessionId(SESSION);
        t.setUserId(ALICE);
        t.setSeq(seq);
        t.setRole(role);
        t.setContent(content);
        return t;
    }

    // ------------------------------------------------------------ the state machine

    @Test
    void opening_is_refused_when_the_session_already_has_a_question() throws Exception {
        givenOwned("active");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION)).thenReturn(List.of(turn(1, "interviewer", "Q1")));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/opening"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message").value("Session already has turns"));

        verifyNoInteractions(ai);
        verify(turns, never()).save(any());
    }

    @Test
    void opening_persists_the_interviewers_first_question() throws Exception {
        givenOwned("active");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION)).thenReturn(List.of());
        when(ai.interviewOpening(SESSION, ALICE)).thenReturn(Map.of(
                "question", "Tell me about a time you fixed a production incident.",
                "meta", Map.of("topic", "incident")));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/opening"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.question.seq").value(1))
                .andExpect(jsonPath("$.data.question.role").value("interviewer"))
                .andExpect(jsonPath("$.data.question.content")
                        .value("Tell me about a time you fixed a production incident."))
                .andExpect(jsonPath("$.data.question.questionMeta.topic").value("incident"));

        ArgumentCaptor<InterviewTurn> saved = ArgumentCaptor.forClass(InterviewTurn.class);
        verify(turns).save(saved.capture());
        assertThat(saved.getValue().getSeq()).isEqualTo(1);
        assertThat(saved.getValue().getRole()).isEqualTo("interviewer");
    }

    @Test
    void answer_is_refused_before_an_opening_question_exists() throws Exception {
        givenOwned("active");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION)).thenReturn(List.of());

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/answer")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"answer\":\"my answer\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message")
                        .value("Start the interview with an opening question first"));

        verifyNoInteractions(ai);
    }

    @Test
    void a_blank_answer_is_a_validation_failure_with_a_field_detail() throws Exception {
        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/answer")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"answer\":\"  \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("answer"));

        verifyNoInteractions(ai);
    }

    @Test
    void an_answer_persists_the_candidate_turn_and_the_followup_when_the_model_asks_one()
            throws Exception {
        givenOwned("active");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION))
                .thenReturn(List.of(turn(1, "interviewer", "Q1")));
        when(ai.interviewAnswer(eq(SESSION), eq("my answer"), eq("Q1"), anyList(), eq(ALICE)))
                .thenReturn(Map.of(
                        "evaluation", Map.of("clarity", 0.8),
                        "next", Map.of("question", "What was the root cause?", "action", "followup",
                                "topic", "incident", "difficulty", 0.7)));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/answer")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"answer\":\"my answer\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.candidateTurn.seq").value(2))
                .andExpect(jsonPath("$.data.candidateTurn.role").value("candidate"))
                .andExpect(jsonPath("$.data.followup.seq").value(3))
                .andExpect(jsonPath("$.data.followup.role").value("interviewer"))
                .andExpect(jsonPath("$.data.followup.content").value("What was the root cause?"))
                .andExpect(jsonPath("$.data.evaluation.clarity").value(0.8));

        // Both turns saved (candidate + interviewer followup), and the difficulty ratchet moved.
        verify(turns, org.mockito.Mockito.times(2)).save(any());
        ArgumentCaptor<InterviewSession> savedSession = ArgumentCaptor.forClass(InterviewSession.class);
        verify(sessions).save(savedSession.capture());
        assertThat(savedSession.getValue().getDifficulty()).isEqualTo(0.7f);
    }

    @Test
    void a_finish_action_persists_no_followup_question() throws Exception {
        // The model says "finish" with a question attached: the candidate's turn is the end
        // of the thread, and a phantom interviewer question would strand the session with an
        // unanswered turn — the exact case the `!"finish".equals(action)` guard exists for.
        givenOwned("active");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION))
                .thenReturn(List.of(turn(1, "interviewer", "Q1")));
        when(ai.interviewAnswer(eq(SESSION), eq("my answer"), eq("Q1"), anyList(), eq(ALICE)))
                .thenReturn(Map.of(
                        "evaluation", Map.of(),
                        "next", Map.of("question", "Any final thoughts?", "action", "finish")));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/answer")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"answer\":\"my answer\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.candidateTurn.seq").value(2))
                .andExpect(jsonPath("$.data.followup").doesNotExist());

        verify(turns, org.mockito.Mockito.times(1)).save(any());
    }

    @Test
    void finalize_is_refused_when_no_turn_exists() throws Exception {
        givenOwned("active");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION)).thenReturn(List.of());

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/finalize"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message").value("Nothing to finalize"));

        verifyNoInteractions(ai);
    }

    @Test
    void finalize_marks_the_session_completed_and_upserts_the_evaluation() throws Exception {
        givenOwned("active");
        InterviewTurn q = turn(1, "interviewer", "Q1");
        InterviewTurn a = turn(2, "candidate", "A1");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION)).thenReturn(List.of(q, a));
        // An evaluation row from a previous finalize: the upsert must reuse it, not add a second.
        InterviewEvaluation existing = new InterviewEvaluation();
        set(existing, "id", UUID.randomUUID());
        existing.setSessionId(SESSION);
        existing.setUserId(ALICE);
        existing.setSummary(Map.of("overall", 60));
        when(evaluations.findBySessionId(SESSION)).thenReturn(Optional.of(existing));
        when(ai.interviewFinalize(eq(SESSION), anyList(), eq(ALICE))).thenReturn(Map.of(
                "evaluation", Map.of(
                        "dims", Map.of("clarity", 0.7),
                        "overall", 85,
                        "what_you_did_well", "concrete examples")));

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/finalize"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.evaluation.id").value(existing.getId().toString()))
                .andExpect(jsonPath("$.data.evaluation.dims.clarity").value(0.7))
                .andExpect(jsonPath("$.data.evaluation.summary.overall").value(85))
                .andExpect(jsonPath("$.data.evaluation.summary.what_you_did_well")
                        .value("concrete examples"))
                .andExpect(jsonPath("$.data.session.status").value("completed"));

        // One save, reusing the row — not a second evaluation for the same session.
        verify(evaluations, org.mockito.Mockito.times(1)).save(any());
        ArgumentCaptor<InterviewSession> saved = ArgumentCaptor.forClass(InterviewSession.class);
        verify(sessions).save(saved.capture());
        assertThat(saved.getValue().getStatus()).isEqualTo("completed");
        assertThat(saved.getValue().getFinishedAt()).isNotNull();
    }

    // ------------------------------------------------------------ patch: what a raw Map may change

    @Test
    void a_patch_updates_only_the_keys_it_names() throws Exception {
        givenOwned("active");

        mvc.perform(patch("/api/v1/interview/sessions/" + SESSION)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"paused\",\"difficulty\":0.8}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("paused"))
                .andExpect(jsonPath("$.data.difficulty").value(0.8))
                .andExpect(jsonPath("$.data.mode").value("mixed"));

        ArgumentCaptor<InterviewSession> saved = ArgumentCaptor.forClass(InterviewSession.class);
        verify(sessions).save(saved.capture());
        assertThat(saved.getValue().getStatus()).isEqualTo("paused");
        assertThat(saved.getValue().getMode()).isEqualTo("mixed");
    }

    @Test
    void a_patch_with_no_recognized_keys_changes_nothing() throws Exception {
        givenOwned("active");

        mvc.perform(patch("/api/v1/interview/sessions/" + SESSION)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"unknownKey\":123}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("active"));

        ArgumentCaptor<InterviewSession> saved = ArgumentCaptor.forClass(InterviewSession.class);
        verify(sessions).save(saved.capture());
        assertThat(saved.getValue().getStatus()).isEqualTo("active");
    }

    // ------------------------------------------------------------ delete + scoping on every route

    @Test
    void delete_answers_204_with_no_body() throws Exception {
        InterviewSession owned = session("active");
        when(sessions.findByIdAndUserId(SESSION, ALICE)).thenReturn(Optional.of(owned));

        mvc.perform(delete("/api/v1/interview/sessions/" + SESSION))
                .andExpect(status().isNoContent())
                .andExpect(content().string(""));

        verify(sessions).delete(owned);
    }

    @Test
    void a_foreign_session_is_404_on_every_route_and_the_ai_client_is_never_called()
            throws Exception {
        // Another user's session answers SESSION_NOT_FOUND ("not yours" and "not there" are
        // the same answer), and — the part worth stating — the AI client is never reached:
        // a foreign caller cannot spend the owner's model budget or append turns to their
        // interview. A leaked call here would be both a data and a billing leak.
        when(sessions.findByIdAndUserId(SESSION, ALICE)).thenReturn(Optional.empty());

        mvc.perform(get("/api/v1/interview/sessions/" + SESSION))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("SESSION_NOT_FOUND"));

        mvc.perform(patch("/api/v1/interview/sessions/" + SESSION)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"paused\"}"))
                .andExpect(status().isNotFound());

        mvc.perform(delete("/api/v1/interview/sessions/" + SESSION))
                .andExpect(status().isNotFound());

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/opening"))
                .andExpect(status().isNotFound());

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/answer")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"answer\":\"x\"}"))
                .andExpect(status().isNotFound());

        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/finalize"))
                .andExpect(status().isNotFound());

        verifyNoInteractions(ai);
        verify(sessions, never()).delete(any());
        verify(turns, never()).save(any());
    }

    @Test
    void an_unauthenticated_caller_is_refused_before_the_service_runs() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/interview/sessions/" + SESSION)).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        mvc.perform(post("/api/v1/interview/sessions/" + SESSION + "/opening"))
                .andExpect(status().isUnauthorized());
        mvc.perform(delete("/api/v1/interview/sessions/" + SESSION)).andExpect(status().isUnauthorized());

        verifyNoInteractions(sessions, turns, ai);
    }

    // ------------------------------------------------------------ detail: turns + evaluation round-trip

    @Test
    void the_detail_route_returns_the_session_with_its_turns_and_evaluation() throws Exception {
        givenOwned("completed");
        when(turns.findBySessionIdOrderBySeqAsc(SESSION))
                .thenReturn(List.of(turn(1, "interviewer", "Q1"), turn(2, "candidate", "A1")));
        InterviewEvaluation evaluation = new InterviewEvaluation();
        set(evaluation, "id", UUID.randomUUID());
        evaluation.setSessionId(SESSION);
        evaluation.setUserId(ALICE);
        evaluation.setDims(Map.of("clarity", 0.9));
        evaluation.setSummary(Map.of("overall", 88));
        when(evaluations.findBySessionId(SESSION)).thenReturn(Optional.of(evaluation));

        mvc.perform(get("/api/v1/interview/sessions/" + SESSION))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.session.status").value("completed"))
                .andExpect(jsonPath("$.data.turns[0].seq").value(1))
                .andExpect(jsonPath("$.data.turns[1].role").value("candidate"))
                .andExpect(jsonPath("$.data.evaluation.dims.clarity").value(0.9))
                .andExpect(jsonPath("$.data.evaluation.summary.overall").value(88));
    }
}
