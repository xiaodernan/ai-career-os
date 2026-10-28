package com.careeros.mail.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.mail.service.MailLinks;
import com.careeros.mail.service.MailList;
import com.careeros.mail.service.MailPreferenceService;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The page a mailbox can open and the POST it can post (roadmap 23.1).
 *
 * <p>What is pinned. The GET renders both dials and changes nothing -- mail scanners prefetch
 * links, so a read that flipped a switch would unsubscribe readers who never clicked. The POST
 * applies exactly the list in its URL and re-renders, so a one-click from the Monday letter
 * cannot silence the morning signals. A forged token, an unknown account and an unknown list
 * are one 404 with no state touched. A scanner's GET on the POST URL is a 405. And the page is
 * {@code no-store}, in the reader's language, and marked noindex, because it states private
 * settings.
 */
class MailPreferenceControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID BOB = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final String SECRET = "test-secret";

    private MailPreferenceService preferences;
    private UserRepository users;
    private MailLinks links;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        preferences = mock(MailPreferenceService.class);
        users = mock(UserRepository.class);
        links = new MailLinks(SECRET, "https://careeros.example");
        mvc = MockMvcBuilders.standaloneSetup(
                        new MailPreferenceController(preferences, links, users))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .build();
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "en")));
        when(users.findById(BOB)).thenReturn(Optional.of(account(BOB, "en")));
        when(preferences.receives(any(), any())).thenReturn(true);
    }

    private static User account(UUID id, String locale) {
        User user = new User();
        user.setId(id);
        user.setEmail(id + "@example.com");
        user.setLocale(locale);
        return user;
    }

    private String url(String action) {
        return "/api/v1/mail/preferences/" + ALICE + "/" + links.token(ALICE)
                + (action.isEmpty() ? "" : "/" + action);
    }

    private String body(MvcResult result) throws Exception {
        return result.getResponse().getContentAsString(StandardCharsets.UTF_8);
    }

    @Test
    void thePageShowsBothDialsAndChangesNothing() throws Exception {
        MvcResult result = mvc.perform(get(url("")))
                .andExpect(status().isOk())
                .andReturn();

        assertThat(result.getResponse().getContentType()).contains("text/html");
        assertThat(result.getResponse().getHeader("Cache-Control")).contains("no-store");
        assertThat(body(result)).contains(
                "The Monday letter",
                "The morning signals",
                "/stop/weekly",
                "/stop/signals",
                "On");
        verify(preferences, never()).set(any(), any(), anyBoolean());
    }

    @Test
    void aScannerOpeningTheOneClickUrlChangesNothing() throws Exception {
        mvc.perform(get(url("stop/signals")))
                .andExpect(status().isMethodNotAllowed());

        verifyNoInteractions(preferences);
    }

    @Test
    void theOneClickPostStopsItsOwnListAndRendersTheNewState() throws Exception {
        when(preferences.receives(ALICE, MailList.SIGNALS)).thenReturn(false);

        MvcResult result = mvc.perform(post(url("stop/signals")))
                .andExpect(status().isOk())
                .andReturn();

        verify(preferences).set(ALICE, MailList.SIGNALS, false);
        verify(preferences, never()).set(ALICE, MailList.WEEKLY, false);
        assertThat(body(result)).contains("Saved.", "The morning signals", "Off", "/start/signals");
    }

    @Test
    void thePageCanTurnALetterBackOn() throws Exception {
        mvc.perform(post(url("start/weekly")))
                .andExpect(status().isOk());

        verify(preferences).set(ALICE, MailList.WEEKLY, true);
    }

    @Test
    void anotherAccountsSignatureIsTheSame404AsAnUnknownAccount() throws Exception {
        String forged = "/api/v1/mail/preferences/" + ALICE + "/" + links.token(BOB);

        mvc.perform(get(forged)).andExpect(status().isNotFound());
        mvc.perform(post(forged + "/stop/signals")).andExpect(status().isNotFound());

        verifyNoInteractions(preferences);
    }

    @Test
    void anUnknownListIsTheSame404() throws Exception {
        mvc.perform(post(url("stop/monthly")))
                .andExpect(status().isNotFound());

        verifyNoInteractions(preferences);
    }

    @Test
    void aDeletedAccountIsTheSame404() throws Exception {
        when(users.findById(ALICE)).thenReturn(Optional.empty());

        mvc.perform(get(url(""))).andExpect(status().isNotFound());

        verifyNoInteractions(preferences);
    }

    @Test
    void aChineseAccountGetsThePageInChinese() throws Exception {
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "zh")));

        MvcResult result = mvc.perform(get(url("")))
                .andExpect(status().isOk())
                .andReturn();

        assertThat(body(result)).contains("lang=\"zh\"", "周一信", "每日信号", "开");
    }
}
