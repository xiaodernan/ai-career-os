package com.careeros.calendar.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.calendar.service.CalendarLinks;
import com.careeros.calendar.service.CalendarService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The two calendar routes (roadmap 34.1).
 *
 * <p>The feed is the only public route this unit adds, so its claims are about what a stranger
 * holding the URL can and cannot do. The signed token opens exactly one account's feed, in that
 * account's language; a forged token, another secret's token, an unreadable one and a missing
 * one are the same 404 sentence, and a token naming an erased account is that sentence too, so
 * the open internet cannot tell which half of a guess was right. The answer is the document
 * itself -- the body must not be wrapped in the API envelope, or a calendar client would reject
 * the whole feed -- and it is neither stored nor indexed, because it names the reader's board.
 *
 * <p>The address is handed out only to a session. That is the whole point of the link: the
 * reader asks for it once while signed in, and from then on the calendar app is the only
 * holder.
 */
class CalendarControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String DOCUMENT = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n";

    private CalendarLinks links;
    private CalendarService calendar;
    private UserRepository users;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        links = new CalendarLinks("test-secret", "https://careeros.example");
        calendar = mock(CalendarService.class);
        users = mock(UserRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(new CalendarController(links, calendar, users))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "en")));
        when(calendar.feed(ALICE, "en")).thenReturn(DOCUMENT);
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private static User account(UUID id, String locale) {
        User user = new User();
        user.setId(id);
        user.setEmail(id + "@example.invalid");
        user.setLocale(locale);
        return user;
    }

    @Test
    void aSignedTokenAnswersTheCalendarDocumentAndNoEnvelope() throws Exception {
        mvc.perform(get("/api/v1/calendar.ics").param("token", links.token(ALICE)))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("text/calendar"))
                .andExpect(content().string(DOCUMENT))
                .andExpect(header().string("Cache-Control", "no-store"))
                .andExpect(header().string("X-Robots-Tag", "noindex"));
    }

    @Test
    void theFeedIsWrittenInTheAccountsLanguage() throws Exception {
        when(users.findById(ALICE)).thenReturn(Optional.of(account(ALICE, "zh-CN")));
        when(calendar.feed(ALICE, "zh-CN")).thenReturn(DOCUMENT);

        mvc.perform(get("/api/v1/calendar.ics").param("token", links.token(ALICE)))
                .andExpect(status().isOk());

        verify(calendar).feed(ALICE, "zh-CN");
    }

    @Test
    void aForgedForeignUnreadableOrMissingTokenIsTheSame404() throws Exception {
        String token = links.token(ALICE);
        String forged = (token.charAt(0) == 'A' ? "B" : "A") + token.substring(1);
        String wrongSecret = new CalendarLinks("another-secret", "https://careeros.example").token(ALICE);

        for (String presented : List.of(forged, wrongSecret, "not base64 !!!")) {
            mvc.perform(get("/api/v1/calendar.ics").param("token", presented))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.error.code").value("CALENDAR_LINK_INVALID"));
        }
        mvc.perform(get("/api/v1/calendar.ics"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("CALENDAR_LINK_INVALID"));
        verifyNoInteractions(calendar);
    }

    @Test
    void aValidTokenForAnErasedAccountIsTheSame404() throws Exception {
        when(users.findById(ALICE)).thenReturn(Optional.empty());

        mvc.perform(get("/api/v1/calendar.ics").param("token", links.token(ALICE)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("CALENDAR_LINK_INVALID"));
        verifyNoInteractions(calendar);
    }

    @Test
    void theSignedInAccountIsHandedAnAddressThatSignsBackToIt() throws Exception {
        String body = mvc.perform(get("/api/v1/calendar/link"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.url").value(links.feed(ALICE)))
                .andReturn().getResponse().getContentAsString();

        assertThat(body).contains("https://careeros.example/api/v1/calendar.ics?token=");
        assertThat(links.account(links.token(ALICE))).isEqualTo(ALICE);
    }

    @Test
    void theAddressIsNotHandedOutWithoutASession() throws Exception {
        SecurityContextHolder.clearContext();

        mvc.perform(get("/api/v1/calendar/link"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"));
    }
}
