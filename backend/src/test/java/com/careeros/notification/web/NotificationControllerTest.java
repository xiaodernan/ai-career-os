package com.careeros.notification.web;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.notification.dto.NotificationDtos.Inbox;
import com.careeros.notification.dto.NotificationDtos.NotificationItem;
import com.careeros.notification.service.NotificationService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The inbox routes (roadmap 19.3).
 *
 * <p>Two claims are worth a route-level test. Every handler is handed the caller's id, so one
 * account can never read or dismiss another's state. And a write answers with the fresh inbox
 * rather than a bare acknowledgement: the page showing the list is the page that asked, and it
 * must not have to guess what its own request did.
 */
class NotificationControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID APP = UUID.fromString("22222222-2222-4222-8222-222222222222");

    private NotificationService notifications;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        notifications = mock(NotificationService.class);
        mvc = MockMvcBuilders.standaloneSetup(new NotificationController(notifications))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private static Inbox inbox(int unread) {
        return new Inbox(List.of(new NotificationItem("stale:" + APP + ":1",
                NotificationService.KIND_STALE, "Senior Analyst", "Acme", "applied",
                null, null, "/applications?application=" + APP, OffsetDateTime.now(), unread == 0)),
                unread, OffsetDateTime.now());
    }

    @Test
    void the_inbox_is_the_callers_own() throws Exception {
        when(notifications.inbox(ALICE)).thenReturn(inbox(1));

        mvc.perform(get("/api/v1/notifications"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unread").value(1))
                .andExpect(jsonPath("$.data.items[0].kind").value("stale"))
                .andExpect(jsonPath("$.data.items[0].read").value(false));

        verify(notifications).inbox(ALICE);
    }

    @Test
    void marking_read_binds_the_key_list_and_answers_the_fresh_inbox() throws Exception {
        when(notifications.markRead(eq(ALICE), any())).thenReturn(inbox(0));

        mvc.perform(post("/api/v1/notifications/read")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"keys\":[\"stale:" + APP + ":1\",\"reminder:" + APP + ":2\"]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unread").value(0));

        verify(notifications).markRead(ALICE,
                List.of("stale:" + APP + ":1", "reminder:" + APP + ":2"));
    }

    @Test
    void reading_all_takes_no_body_and_answers_the_fresh_inbox() throws Exception {
        when(notifications.markAllRead(ALICE)).thenReturn(inbox(0));

        mvc.perform(post("/api/v1/notifications/read-all"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unread").value(0));

        verify(notifications).markAllRead(ALICE);
    }

    @Test
    void dismissing_binds_one_key_and_answers_the_fresh_inbox() throws Exception {
        when(notifications.dismiss(eq(ALICE), any())).thenReturn(inbox(0));

        mvc.perform(post("/api/v1/notifications/dismiss")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"key\":\"stale:" + APP + ":1\"}"))
                .andExpect(status().isOk());

        verify(notifications).dismiss(ALICE, "stale:" + APP + ":1");
    }

    @Test
    void a_blank_or_missing_key_is_refused_before_the_service_sees_it() throws Exception {
        mvc.perform(post("/api/v1/notifications/dismiss")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));

        mvc.perform(post("/api/v1/notifications/dismiss")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"key\":\" \"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));

        mvc.perform(post("/api/v1/notifications/read")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"keys\":[]}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));
    }
}
