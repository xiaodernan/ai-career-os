package com.careeros.report.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.report.service.AnalysisService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The analytics routes (Epics 15.1-15.3).
 *
 * <p>All three read the caller's own application rows, so the service hands the
 * engine a list of row-shaped maps. What this pins is that the rows carry the
 * engine's own field names — a row with a snake_case key the engine does not
 * read is a row the engine sees as a title and nothing else — and that the
 * caller's id travels with them.
 *
 * <p>The stage timestamps are the second half of that contract. The application
 * row stores only the current status, so a duration for "how long did the
 * interview take" has one possible source: the status-transition log. These
 * cases pin that the log is what fills `oa_at` and friends, oldest transition
 * first, and that a row without a transition for a stage sends no key for it
 * rather than a null the engine would have to guess about.
 */
class AnalysisControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private com.careeros.ai.AiServiceClient ai;
    private ApplicationRepository applications;
    private com.careeros.application.repository.ApplicationEventRepository events;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ai = mock(com.careeros.ai.AiServiceClient.class);
        applications = mock(ApplicationRepository.class);
        events = mock(com.careeros.application.repository.ApplicationEventRepository.class);
        AnalysisService service = new AnalysisService(ai, applications, events);
        AnalysisController controller = new AnalysisController(service);
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(UUID.fromString(USER), "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private Application application() {
        Application a = new Application();
        // The id and the timestamps are written by the database, so the test
        // fills them the way the persistence layer would: through the fields the
        // entity exposes.
        a.setTitle("Backend Engineer");
        a.setCompanyName("FakeCorp");
        a.setStatus("applied");
        a.setAppliedAt(OffsetDateTime.parse("2026-09-01T00:00:00+00:00"));
        return a;
    }

    @Test
    void the_digest_is_the_engines_answer_wrapped_once() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(ai.insightDigest(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("totalApplications", 1, "stalledCount", 0));

        mvc.perform(get("/api/v1/analysis/insight-digest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.totalApplications").value(1));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> rows = ArgumentCaptor.forClass(List.class);
        verify(ai).insightDigest(eq(UUID.fromString(USER)), rows.capture(), any());
        Map<String, Object> row = rows.getValue().get(0);
        // The engine's own field names: it reads `applied_at` and `created_at`,
        // not the Java column names. A field the row does not carry is left out
        // rather than sent as null -- so `created_at` is absent here, because
        // this row's timestamps are written by the database.
        assertThat(row).containsEntry("status", "applied");
        assertThat(row).containsEntry("company", "FakeCorp");
        assertThat(row).containsEntry("title", "Backend Engineer");
        assertThat(row).containsKey("applied_at");
        assertThat(row).containsKey("id");
        assertThat(row).doesNotContainKey("created_at");
    }

    @Test
    void the_funnel_reads_the_same_rows() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(ai.pipelineFunnel(eq(UUID.fromString(USER)), any()))
                .thenReturn(Map.of("appliedCount", 1, "pipeline", List.of()));

        mvc.perform(get("/api/v1/analysis/pipeline-funnel"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.appliedCount").value(1));

        verify(ai).pipelineFunnel(eq(UUID.fromString(USER)), any());
    }

    @Test
    void the_rates_read_the_same_rows() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(ai.responseRate(eq(UUID.fromString(USER)), any()))
                .thenReturn(Map.of("appliedCount", 1, "responseRate", 0.5));

        mvc.perform(get("/api/v1/analysis/response-rate"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.responseRate").value(0.5));

        verify(ai).responseRate(eq(UUID.fromString(USER)), any());
    }

    /**
     * An account with no applications is a real state, not an error: the
     * engine answers "the funnel is empty", which is the honest digest for a
     * workspace that has not started.
     */
    @Test
    void an_account_with_no_applications_answers_empty_rather_than_failing() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(ai.insightDigest(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("totalApplications", 0));

        mvc.perform(get("/api/v1/analysis/insight-digest"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.totalApplications").value(0));
    }

    /**
     * The reader's language travels with the request. The digest's sentences are the
     * only words in the answer, so the page's locale has to reach the engine; a page
     * that asked in Chinese and got English back would be the same defect U49 fixed,
     * with the languages swapped. Absent means the product default, which the engine
     * owns — the route forwards null rather than inventing a language.
     */
    @Test
    void the_readers_language_travels_to_the_engine() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(ai.insightDigest(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("totalApplications", 0));

        mvc.perform(get("/api/v1/analysis/insight-digest").param("locale", "zh"))
                .andExpect(status().isOk());
        verify(ai).insightDigest(eq(UUID.fromString(USER)), any(), eq("zh"));

        mvc.perform(get("/api/v1/analysis/insight-digest"))
                .andExpect(status().isOk());
        verify(ai).insightDigest(eq(UUID.fromString(USER)), any(), isNull());
    }

    private static final String APP = "2b1c3c4e-1111-2222-3333-444444444444";

    /**
     * An application as the persistence layer hands it back: stamped with an id.
     * {@code id}, {@code created_at} and {@code updated_at} have no setters because
     * Hibernate writes them, so the test writes them the way the entity does.
     */
    private Application stamped(String status) {
        Application a = new Application();
        a.setTitle("Backend Engineer");
        a.setCompanyName("FakeCorp");
        a.setStatus(status);
        a.setAppliedAt(OffsetDateTime.parse("2026-09-01T09:00:30+00:00"));
        ReflectionTestUtils.setField(a, "id", UUID.fromString(APP));
        return a;
    }

    /** One entry of the status-transition log, as {@code applyStatusChange} writes it. */
    private static ApplicationEvent transition(String to, String at) {
        ApplicationEvent event = new ApplicationEvent();
        event.setApplicationId(UUID.fromString(APP));
        event.setUserId(UUID.fromString(USER));
        event.setKind("status");
        event.setPayload(Map.of("from", "applied", "to", to));
        ReflectionTestUtils.setField(event, "createdAt", OffsetDateTime.parse(at));
        return event;
    }

    /** The row the digest would be sent, for one application and one transition log. */
    private Map<String, Object> rowFor(Application app, List<ApplicationEvent> log) throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(app)));
        when(events.findByUserIdAndKindOrderByCreatedAtAscIdAsc(UUID.fromString(USER), "status"))
                .thenReturn(log);
        when(ai.insightDigest(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("totalApplications", 1));

        mvc.perform(get("/api/v1/analysis/insight-digest")).andExpect(status().isOk());

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> rows = ArgumentCaptor.forClass(List.class);
        verify(ai).insightDigest(eq(UUID.fromString(USER)), rows.capture(), any());
        return rows.getValue().get(0);
    }

    /**
     * The engine times a stage from the moment it was entered, and only the transition log
     * knows that moment -- the application row carries the current status alone. Without
     * these keys the engine's {@code timeInStage} answers "no data" for every stage of every
     * candidate, which is what the response-rate route did while it promised durations.
     */
    @Test
    void a_status_transition_becomes_the_stage_timestamp_the_engine_times() throws Exception {
        Map<String, Object> row = rowFor(stamped("interview"), List.of(
                transition("oa", "2026-09-05T09:00:30+00:00"),
                transition("interview", "2026-09-12T09:00:30+00:00")));

        assertThat(row).containsEntry("oa_at", "2026-09-05T09:00:30Z");
        assertThat(row).containsEntry("interview_at", "2026-09-12T09:00:30Z");
        // A stage the log never records sends no key at all, not a null: the engine
        // omits the application from that stage's sample rather than timing it from nothing.
        assertThat(row).doesNotContainKey("final_round_at");
        assertThat(row).doesNotContainKey("offer_at");
    }

    /**
     * Re-entering a stage must not move the clock. A candidate who is pushed back to
     * {@code applied} and reaches {@code interview} again still reached it the first time,
     * and a duration read from the second visit would understate the pipeline.
     */
    @Test
    void the_oldest_transition_wins_when_a_stage_is_reentered() throws Exception {
        Map<String, Object> row = rowFor(stamped("interview"), List.of(
                transition("interview", "2026-09-12T09:00:30+00:00"),
                transition("applied", "2026-09-15T09:00:30+00:00"),
                transition("interview", "2026-09-20T09:00:30+00:00")));

        assertThat(row).containsEntry("interview_at", "2026-09-12T09:00:30Z");
    }

    /**
     * The timed stages are the engine's pipeline, not every status it can hold. A
     * rejection is not a stage you reached, and {@code applied} is the row's own
     * {@code applied_at} -- letting either of those keys in would hand the engine a
     * duration for a stage whose name it does not know.
     */
    @Test
    void a_transition_to_an_untimed_status_adds_no_stage_key() throws Exception {
        Map<String, Object> row = rowFor(stamped("rejected"), List.of(
                transition("applied", "2026-09-02T09:00:30+00:00"),
                transition("rejected", "2026-09-18T09:00:30+00:00")));

        assertThat(row).doesNotContainKey("rejected_at");
        assertThat(row).containsEntry("applied_at", "2026-09-01T09:00:30Z");
    }

    /**
     * The row's own last activity travels as {@code last_seen}. The digest calls the number
     * it builds from it {@code daysSinceLastActivity}, so a candidate who annotated an
     * application yesterday and applied in April is not stalled for 40 days.
     */
    @Test
    void the_row_updated_column_travels_as_last_seen() throws Exception {
        Application app = stamped("applied");
        ReflectionTestUtils.setField(app, "updatedAt",
                OffsetDateTime.parse("2026-09-19T09:00:30+00:00"));

        Map<String, Object> row = rowFor(app, List.of());

        assertThat(row).containsEntry("last_seen", "2026-09-19T09:00:30Z");
    }
}
