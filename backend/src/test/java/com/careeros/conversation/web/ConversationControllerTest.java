package com.careeros.conversation.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.ArgumentMatchers.eq;
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
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.conversation.entity.Conversation;
import com.careeros.conversation.entity.Message;
import com.careeros.conversation.repository.ConversationDigestRepository;
import com.careeros.conversation.repository.ConversationRepository;
import com.careeros.conversation.repository.MessageRepository;
import com.careeros.conversation.service.ConversationService;
import com.careeros.support.TestTransactions;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The copilot's conversation surface: list, read, rename, delete, history. Service-level
 * tests exist for the list digests and the preview text, but nothing knocked on PATCH, DELETE
 * or GET /{id}/messages — the three routes the sidebar's row actions reach. The copilot
 * client's own tests only cover the chat turn.
 *
 * The service runs for real here (mocked repositories): the two contracts worth stating are
 * (1) "null means unchanged, and a blank title is not a title" — a rename that wipes the
 * title would strand every untitled chat as "" in the sidebar, and (2) scoping: a
 * conversation belonging to somebody else answers CONVERSATION_NOT_FOUND (404) on all three
 * mutating routes, and the repository's delete is never reached with a foreign row.
 */
class ConversationControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID CHAT = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private ConversationRepository conversations;
    private MessageRepository messages;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        conversations = mock(ConversationRepository.class);
        // save() returns the row it was handed (JPA's persist/merge contract); Mockito's
        // default null would NPE the service's toItem(conversations.save(c)) on every write.
        when(conversations.save(any())).thenAnswer(inv -> inv.getArgument(0));
        messages = mock(MessageRepository.class);
        ConversationDigestRepository digests = mock(ConversationDigestRepository.class);
        when(digests.forConversations(anyCollection())).thenReturn(Map.of());
        AiServiceClient ai = mock(AiServiceClient.class);
        ConversationService service =
                new ConversationService(conversations, messages, digests, ai,
                        TestTransactions.executing());
        mvc = MockMvcBuilders.standaloneSetup(new ConversationController(service))
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

    /**
     * {@code id} is {@code @UuidGenerator}-managed and {@code createdAt} is
     * {@code @CreationTimestamp}-managed, so neither has a setter: reflection is how a
     * detached row gets the values the running app's persistence layer would assign.
     */
    private static void set(Object target, String field, Object value) {
        try {
            java.lang.reflect.Field f = target.getClass().getDeclaredField(field);
            f.setAccessible(true);
            f.set(target, value);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("cannot set " + field, e);
        }
    }

    private static Conversation chat(UUID owner, String title, Map<String, Object> context) {
        Conversation c = new Conversation();
        set(c, "id", CHAT);
        c.setUserId(owner);
        c.setTitle(title);
        if (context != null) {
            c.setContext(context);
        }
        return c;
    }

    private void givenOwned(String title, Map<String, Object> context) {
        when(conversations.findByIdAndUserId(CHAT, ALICE)).thenReturn(Optional.of(chat(ALICE, title, context)));
    }

    // ------------------------------------------------------------ read

    @Test
    void a_single_row_read_answers_null_aggregates_rather_than_claiming_an_empty_thread()
            throws Exception {
        // The DTO's own claim: lastMessagePreview and messageCount are filled only where the
        // caller asked for a page — a single-row read has not looked at the thread, so both
        // stay null rather than claiming an empty chat.
        givenOwned("How do I price myself?", null);

        mvc.perform(get("/api/v1/conversations/" + CHAT))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.id").value(CHAT.toString()))
                .andExpect(jsonPath("$.data.title").value("How do I price myself?"))
                .andExpect(jsonPath("$.data.lastMessagePreview").doesNotExist())
                .andExpect(jsonPath("$.data.messageCount").doesNotExist());
    }

    @Test
    void the_sidebar_page_fills_the_preview_and_count_from_the_digest() throws Exception {
        Conversation owned = chat(ALICE, "Chat about Kafka", null);
        when(conversations.findByUserIdOrderByUpdatedAtDescIdAsc(eq(ALICE), any()))
                .thenReturn(new PageImpl<>(List.of(owned), PageRequest.of(0, 20), 1));
        ConversationDigestRepository digests = mock(ConversationDigestRepository.class);
        when(digests.forConversations(anyCollection())).thenReturn(Map.of(CHAT,
                new ConversationDigestRepository.Digest("Streams vs KSQL, folded to one line", 7)));

        ConversationService service = new ConversationService(conversations, messages, digests,
                mock(AiServiceClient.class), TestTransactions.executing());
        MockMvc pageMvc = MockMvcBuilders.standaloneSetup(new ConversationController(service))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();

        pageMvc.perform(get("/api/v1/conversations"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].id").value(CHAT.toString()))
                .andExpect(jsonPath("$.data.items[0].lastMessagePreview")
                        .value("Streams vs KSQL, folded to one line"))
                .andExpect(jsonPath("$.data.items[0].messageCount").value(7))
                .andExpect(jsonPath("$.data.total").value(1));
    }

    @Test
    void the_history_route_returns_the_thread_in_order_with_its_artifacts() throws Exception {
        givenOwned("Chat", null);
        Message first = message("user", "hello", OffsetDateTime.parse("2026-10-01T10:00:00Z"));
        Message second = message("assistant", "hi there", OffsetDateTime.parse("2026-10-01T10:00:05Z"));
        second.setAgentRunId(UUID.fromString("44444444-4444-4444-4444-444444444444"));
        when(messages.findByConversationIdOrderByCreatedAtAsc(CHAT)).thenReturn(List.of(first, second));

        mvc.perform(get("/api/v1/conversations/" + CHAT + "/messages"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].role").value("user"))
                .andExpect(jsonPath("$.data[0].content").value("hello"))
                .andExpect(jsonPath("$.data[1].role").value("assistant"))
                .andExpect(jsonPath("$.data[1].agentRunId")
                        .value("44444444-4444-4444-4444-444444444444"));
    }

    // ------------------------------------------------------------ rename: null unchanged, blank not a title

    @Test
    void a_rename_trims_the_title_and_leaves_the_context_alone() throws Exception {
        givenOwned("old title", Map.of("job", "job-1"));

        mvc.perform(patch("/api/v1/conversations/" + CHAT)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"  new title  \"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.title").value("new title"))
                .andExpect(jsonPath("$.data.context.job").value("job-1"));

        ArgumentCaptor<Conversation> saved = ArgumentCaptor.forClass(Conversation.class);
        verify(conversations).save(saved.capture());
        assertThat(saved.getValue().getTitle()).isEqualTo("new title");
        assertThat(saved.getValue().getContext()).containsEntry("job", "job-1");
    }

    @Test
    void a_blank_title_is_not_a_title_and_never_replaces_the_real_one() throws Exception {
        // The service guards every title write with `!= null && !isBlank()`. Without that
        // guard a rename to "" would strand the chat as an empty row in the sidebar, where
        // nothing identifies it. A blank title is ignored, the same way null is.
        givenOwned("How do I price myself?", null);

        mvc.perform(patch("/api/v1/conversations/" + CHAT)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"   \"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.title").value("How do I price myself?"));

        ArgumentCaptor<Conversation> saved = ArgumentCaptor.forClass(Conversation.class);
        verify(conversations).save(saved.capture());
        assertThat(saved.getValue().getTitle()).isEqualTo("How do I price myself?");
    }

    @Test
    void a_context_only_patch_leaves_the_title_alone() throws Exception {
        givenOwned("keep me", Map.of("job", "job-1"));

        mvc.perform(patch("/api/v1/conversations/" + CHAT)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"context\":{\"job\":\"job-2\"}}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.title").value("keep me"))
                .andExpect(jsonPath("$.data.context.job").value("job-2"));
    }

    @Test
    void an_oversized_title_is_refused_before_the_service_sees_it() throws Exception {
        mvc.perform(patch("/api/v1/conversations/" + CHAT)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"" + "x".repeat(201) + "\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.error.details[0].field").value("title"));

        verifyNoInteractions(conversations);
    }

    // ------------------------------------------------------------ scoping on all three routes

    @Test
    void a_foreign_conversation_is_404_on_read_and_the_page_asks_for_no_messages() throws Exception {
        when(conversations.findByIdAndUserId(CHAT, ALICE)).thenReturn(Optional.empty());

        mvc.perform(get("/api/v1/conversations/" + CHAT))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("CONVERSATION_NOT_FOUND"));

        mvc.perform(get("/api/v1/conversations/" + CHAT + "/messages"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("CONVERSATION_NOT_FOUND"));

        verify(messages, never()).findByConversationIdOrderByCreatedAtAsc(any());
    }

    @Test
    void a_foreign_conversation_is_404_on_rename_and_nothing_is_saved() throws Exception {
        when(conversations.findByIdAndUserId(CHAT, ALICE)).thenReturn(Optional.empty());

        mvc.perform(patch("/api/v1/conversations/" + CHAT)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"stolen\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("CONVERSATION_NOT_FOUND"));

        verify(conversations, never()).save(any());
    }

    @Test
    void delete_answers_204_on_204_with_no_body_and_forgets_only_your_own_row() throws Exception {
        Conversation owned = chat(ALICE, "old chat", null);
        when(conversations.findByIdAndUserId(CHAT, ALICE)).thenReturn(Optional.of(owned));

        mvc.perform(delete("/api/v1/conversations/" + CHAT))
                .andExpect(status().isNoContent())
                .andExpect(content().string(""));

        verify(conversations).delete(owned);
    }

    @Test
    void a_foreign_conversation_is_404_on_delete_and_the_repository_is_never_told() throws Exception {
        when(conversations.findByIdAndUserId(CHAT, ALICE)).thenReturn(Optional.empty());

        mvc.perform(delete("/api/v1/conversations/" + CHAT))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("CONVERSATION_NOT_FOUND"));

        verify(conversations, never()).delete(any());
    }

    // ------------------------------------------------------------ who is asking

    @Test
    void an_unauthenticated_caller_is_refused_before_the_service_runs() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/conversations/" + CHAT)).andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
        mvc.perform(patch("/api/v1/conversations/" + CHAT)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}")).andExpect(status().isUnauthorized());
        mvc.perform(delete("/api/v1/conversations/" + CHAT)).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/conversations/" + CHAT + "/messages"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(conversations, messages);
    }

    private static Message message(String role, String content, OffsetDateTime createdAt) {
        Message m = new Message();
        set(m, "id", UUID.randomUUID());
        m.setConversationId(CHAT);
        m.setUserId(ALICE);
        m.setRole(role);
        m.setContent(content);
        set(m, "createdAt", createdAt);
        return m;
    }
}
