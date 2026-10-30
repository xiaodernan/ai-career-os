package com.careeros.mail.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The settings route that does not need a letter (roadmap 42.1).
 *
 * <p>What is pinned. A signed-in reader is handed the same signed page the letters carry, so the
 * screen and the mailbox open one document. Each of the three booleans comes from the column its
 * sweep reads, so the card cannot claim a letter is on while the sweep subtracts the account. No
 * session means no settings. And the answer is {@code no-store} and noindex: the URL in it is a
 * credential that can change private settings, so a cache must not keep it.
 */
class MailSettingsControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String SECRET = "test-secret";

    private MailPreferenceService preferences;
    private MailLinks links;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        preferences = mock(MailPreferenceService.class);
        links = new MailLinks(SECRET, "https://careeros.example");
        mvc = MockMvcBuilders.standaloneSetup(new MailSettingsController(preferences, links))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        when(preferences.receives(ALICE, MailList.WEEKLY)).thenReturn(true);
        when(preferences.receives(ALICE, MailList.SIGNALS)).thenReturn(true);
        when(preferences.receives(ALICE, MailList.REMINDERS)).thenReturn(true);
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void theSignedInReaderIsHandedThePageTheLettersWouldOpen() throws Exception {
        String body = mvc.perform(get("/api/v1/me/mail/settings"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.url").value(links.page(ALICE)))
                .andExpect(jsonPath("$.data.weekly").value(true))
                .andExpect(jsonPath("$.data.signals").value(true))
                .andExpect(jsonPath("$.data.reminders").value(true))
                .andReturn().getResponse().getContentAsString();

        assertThat(body).contains("https://careeros.example/api/v1/mail/preferences/" + ALICE);
        assertThat(links.valid(ALICE, links.token(ALICE))).isTrue();
    }

    @Test
    void eachDialIsReportedFromTheColumnItsSweepReads() throws Exception {
        when(preferences.receives(ALICE, MailList.WEEKLY)).thenReturn(false);
        when(preferences.receives(ALICE, MailList.REMINDERS)).thenReturn(false);

        mvc.perform(get("/api/v1/me/mail/settings"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.weekly").value(false))
                .andExpect(jsonPath("$.data.signals").value(true))
                .andExpect(jsonPath("$.data.reminders").value(false));
    }

    @Test
    void thePageAddressIsNeitherStoredNorIndexed() throws Exception {
        mvc.perform(get("/api/v1/me/mail/settings"))
                .andExpect(status().isOk())
                .andExpect(header().string("Cache-Control", "no-store"))
                .andExpect(header().string("X-Robots-Tag", "noindex"));
    }

    @Test
    void theSettingsAreNotHandedOutWithoutASession() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/me/mail/settings"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
    }
}
