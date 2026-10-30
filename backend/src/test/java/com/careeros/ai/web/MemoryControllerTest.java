package com.careeros.ai.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
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
 * The memory routes existed in the controller without a single test knocking on them: grep
 * for "memories" under backend/src/test returned nothing before this file, while the routes
 * are the browser's only way to correct a fact the extractor got wrong (PRD §17). The write
 * side — chat extraction — is covered end to end; nothing covered the three routes that read,
 * correct and forget.
 *
 * Standalone setup installs the production advice, the production exception handler and the
 * production {@link CurrentUserArgumentResolver}, so a request travels the same three
 * decisions it travels in the running app: who is asking (the resolver), what is validated
 * (the DTO's constraints and the path variable's type), and how the answer is shaped (the
 * envelope). The client is the one mock: its replies are this controller's entire world, and
 * its 404 ("not yours" and "not there" are the same answer in the ai-service's WHERE clause)
 * arrives as the {@link ApiException} {@code HttpAiServiceClient} now translates upstream
 * status codes into.
 */
class MemoryControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID MEMORY = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private AiServiceClient ai;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        mvc = MockMvcBuilders.standaloneSetup(new MemoryController(ai))
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

    private static Map<String, Object> row(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], kv[i + 1]);
        }
        return m;
    }

    private static Map<String, Object> fullRow() {
        return row("id", MEMORY.toString(), "kind", "skill", "key", "kafka",
                "content", "knows Kafka streams", "importance", 0.8,
                "source", "conversation",
                "createdAt", "2026-10-01 10:00:00", "updatedAt", "2026-10-02 11:00:00");
    }

    // ------------------------------------------------------------ list

    @Test
    void the_list_answers_the_envelope_and_forwards_the_callers_id() throws Exception {
        when(ai.listMemories(any(), eq(ALICE))).thenReturn(List.of(fullRow()));

        mvc.perform(get("/api/v1/memories"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data[0].id").value(MEMORY.toString()))
                .andExpect(jsonPath("$.data[0].kind").value("skill"))
                .andExpect(jsonPath("$.data[0].key").value("kafka"))
                .andExpect(jsonPath("$.data[0].content").value("knows Kafka streams"))
                .andExpect(jsonPath("$.data[0].importance").value(0.8))
                .andExpect(jsonPath("$.data[0].source").value("conversation"))
                .andExpect(jsonPath("$.data[0].createdAt").value("2026-10-01 10:00:00"))
                .andExpect(jsonPath("$.data[0].updatedAt").value("2026-10-02 11:00:00"))
                // The wire carries the kind, not a word for it: the browser draws the
                // badge from the translation table, so a `label` here would be a second
                // spelling of the same vocabulary with no reader.
                .andExpect(jsonPath("$.data[0].label").doesNotExist());
    }

    @Test
    void the_kinds_filter_reaches_the_client_and_an_empty_list_is_an_empty_answer() throws Exception {
        when(ai.listMemories(eq(List.of("skill", "goal")), eq(ALICE))).thenReturn(List.of());

        mvc.perform(get("/api/v1/memories").param("kinds", "skill,goal"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").isEmpty());

        // No kinds parameter means "everything the extractor wrote", which is a null filter,
        // not an empty one — an empty list would ask the ai-service for no kind at all.
        mvc.perform(get("/api/v1/memories")).andExpect(status().isOk());
        verify(ai).listMemories(null, ALICE);
    }

    @Test
    void a_row_missing_keys_renders_nulls_rather_than_failing_the_page() throws Exception {
        // The mapper's own claim: a missing key is null, because the page it feeds has to
        // say "no memories" or show a partial row rather than 500 on one unexpected shape.
        when(ai.listMemories(any(), eq(ALICE))).thenReturn(List.of(row("kind", "goal")));

        mvc.perform(get("/api/v1/memories"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").doesNotExist())
                .andExpect(jsonPath("$.data[0].kind").value("goal"))
                .andExpect(jsonPath("$.data[0].importance").doesNotExist());
    }

    // ------------------------------------------------------------ patch

    @Test
    void the_patch_forwards_the_correction_and_answers_the_row_it_became() throws Exception {
        when(ai.patchMemory(eq(MEMORY), eq("knows Kafka and Flink"), eq(0.5), eq(ALICE)))
                .thenReturn(fullRow());

        mvc.perform(patch("/api/v1/memories/" + MEMORY)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"content\":\"knows Kafka and Flink\",\"importance\":0.5}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.id").value(MEMORY.toString()))
                .andExpect(jsonPath("$.data.content").value("knows Kafka streams"));
    }

    @Test
    void an_importance_only_correction_forwards_null_content() throws Exception {
        // "Either field, not both": a fact the user is tired of being reminded about only
        // needs its weight lowered, and requiring content would make the caller invent one.
        when(ai.patchMemory(eq(MEMORY), eq(null), eq(0.1), eq(ALICE))).thenReturn(fullRow());

        mvc.perform(patch("/api/v1/memories/" + MEMORY)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"importance\":0.1}"))
                .andExpect(status().isOk());

        ArgumentCaptor<String> content = ArgumentCaptor.forClass(String.class);
        verify(ai).patchMemory(eq(MEMORY), content.capture(), eq(0.1), eq(ALICE));
        assertThat(content.getValue()).isNull();
    }

    @Test
    void a_malformed_id_is_a_400_the_framework_writes_and_the_client_is_never_asked()
            throws Exception {
        // The path variable is a UUID, not a String plus a parse: the framework's own
        // type-mismatch handler answers 400 MALFORMED_REQUEST. Before that change
        // UUID.fromString threw IllegalArgumentException, the catch-all answered 500,
        // and a typo in the URL looked like our bug instead of the caller's.
        mvc.perform(patch("/api/v1/memories/not-a-uuid")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"importance\":0.1}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("MALFORMED_REQUEST"));

        verifyNoInteractions(ai);
    }

    @Test
    void an_out_of_range_correction_is_refused_before_the_client_sees_it() throws Exception {
        mvc.perform(patch("/api/v1/memories/" + MEMORY)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"importance\":1.5}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("importance"))
                .andExpect(jsonPath("$.error.details[0].message")
                        .value("importance must be between 0 and 1"));

        mvc.perform(patch("/api/v1/memories/" + MEMORY)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"content\":\"" + "x".repeat(4001) + "\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.details[0].field").value("content"));

        verifyNoInteractions(ai);
    }

    @Test
    void a_foreign_memory_surfaces_the_upstreams_404_not_a_502() throws Exception {
        // The one claim the controller's docstring makes that only the transport can keep:
        // "not yours" and "not there" are the same answer. HttpAiServiceClient.translateStatus
        // turns the ai-service's 404 into ApiException(NOT_FOUND); before that translation
        // existed every upstream status was flattened to one 502, so a
        // browser correcting someone else's id was told the AI service had failed.
        when(ai.patchMemory(eq(MEMORY), eq("x"), eq(null), eq(ALICE)))
                .thenThrow(new ApiException(ApiErrorCode.NOT_FOUND, "Resource not found"));

        mvc.perform(patch("/api/v1/memories/" + MEMORY)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"content\":\"x\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("NOT_FOUND"));
    }

    // ------------------------------------------------------------ delete

    @Test
    void the_delete_forwards_the_callers_id_and_answers_204() throws Exception {
        mvc.perform(delete("/api/v1/memories/" + MEMORY))
                .andExpect(status().isNoContent())
                .andExpect(content().string(""));

        verify(ai).deleteMemory(MEMORY, ALICE);
    }

    @Test
    void a_missing_or_foreign_memory_is_a_404_on_delete_too() throws Exception {
        org.mockito.Mockito.doThrow(new ApiException(ApiErrorCode.NOT_FOUND, "Resource not found"))
                .when(ai).deleteMemory(MEMORY, ALICE);

        mvc.perform(delete("/api/v1/memories/" + MEMORY))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("NOT_FOUND"));
    }

    @Test
    void a_malformed_id_is_a_400_on_delete_and_the_client_is_never_asked() throws Exception {
        mvc.perform(delete("/api/v1/memories/not-a-uuid"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("MALFORMED_REQUEST"));

        verify(ai, never()).deleteMemory(any(), any());
    }

    // ------------------------------------------------------------ who is asking

    @Test
    void an_unauthenticated_caller_is_refused_by_the_resolver_before_the_route_runs()
            throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/memories")).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.error.message").value("Authentication required"));
        mvc.perform(patch("/api/v1/memories/" + MEMORY)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"importance\":0.1}"))
                .andExpect(status().isUnauthorized());
        mvc.perform(delete("/api/v1/memories/" + MEMORY)).andExpect(status().isUnauthorized());

        verifyNoInteractions(ai);
    }

    @Test
    void the_callers_id_is_the_principals_and_never_the_bodys() throws Exception {
        // The scoping rule, in the only place it can be stated truthfully: the id the client
        // is handed comes from the SecurityContext, and no field of the request body can
        // reach it. A body claiming another user changes nothing about whose rows are read.
        when(ai.listMemories(any(), any())).thenReturn(List.of(fullRow()));

        mvc.perform(get("/api/v1/memories"))
                .andExpect(status().isOk());

        ArgumentCaptor<UUID> scoped = ArgumentCaptor.forClass(UUID.class);
        verify(ai).listMemories(any(), scoped.capture());
        assertThat(scoped.getValue()).isEqualTo(ALICE);

        // And a different principal scopes to itself, not to ALICE.
        UUID bob = UUID.fromString("22222222-2222-4222-8222-222222222222");
        as(bob);
        mvc.perform(get("/api/v1/memories")).andExpect(status().isOk());

        verify(ai).listMemories(any(), eq(bob));
    }
}
