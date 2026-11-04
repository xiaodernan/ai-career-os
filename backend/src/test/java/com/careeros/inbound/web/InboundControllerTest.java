package com.careeros.inbound.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.common.PageDTO;
import com.careeros.inbound.dto.InboundMailDtos.InboundMailItem;
import com.careeros.inbound.dto.InboundMailDtos.IntentCount;
import com.careeros.inbound.dto.InboundMailDtos.IntentCounts;
import com.careeros.inbound.service.InboundLinks;
import com.careeros.inbound.service.InboundMailService;
import com.careeros.inbound.service.InboundReplyService;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Pageable;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The reply's two doors (roadmap 37.1), and the reader's side of them (37.3).
 *
 * <p>The webhook is public by construction -- a provider holds no session -- so its claims are
 * about what a stranger with the URL can do: post a letter, and get the same acknowledgement
 * whether the token is real or forged (here the service's own 404, since the credential is its
 * business). The address route is the signed-in half: it hands out one account's address, and
 * a deployment with no receiving domain answers a 503 that says so instead of an address that
 * would bounce. The replies page and the file write are the signed-in account's own: the page
 * asks for the first window by default, and a letter that is not the caller's is refused with
 * the same 404 whether it never existed or belongs to someone else.
 */
class InboundControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID MAIL = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID APP = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private InboundLinks links;
    private InboundMailService mail;
    private InboundReplyService replies;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        links = new InboundLinks("test-secret", "inbox.careeros.example");
        mail = mock(InboundMailService.class);
        replies = mock(InboundReplyService.class);
        mvc = MockMvcBuilders.standaloneSetup(new InboundController(links, mail, replies))
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

    @Test
    void theSignedInAccountIsHandedItsOwnAddress() throws Exception {
        mvc.perform(get("/api/v1/inbound/link"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.address").value(links.address(ALICE)));

        verifyNoInteractions(mail);
    }

    @Test
    void aDeploymentWithoutAReceivingDomainSaysSoRatherThanHandingOutABouncingAddress() throws Exception {
        mvc = MockMvcBuilders.standaloneSetup(
                        new InboundController(new InboundLinks("test-secret", ""), mail, replies))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();

        mvc.perform(get("/api/v1/inbound/link"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("INBOUND_NOT_CONFIGURED"));
    }

    @Test
    void theProviderPostsOneLetterAndIsAcknowledgedWithoutALetter() throws Exception {
        mvc.perform(post("/api/v1/inbound/mail/{token}", "abc.def")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"MessageID":"<abc@mail>","From":"ada@example.com",
                                 "Subject":"Your application","TextBody":"Hello",
                                 "Date":"2019-06-05T16:53:08-05:00"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("received"));

        verify(mail).receive(argThat(token -> "abc.def".equals(token)), argThat(payload ->
                "<abc@mail>".equals(payload.messageId())
                        && "ada@example.com".equals(payload.from())
                        && "Your application".equals(payload.subject())
                        && "Hello".equals(payload.textBody())
                        && "2019-06-05T16:53:08-05:00".equals(payload.date())));
    }

    @Test
    void aForgedTokenIsTheServicesOwn404InTheStandardEnvelope() throws Exception {
        when(mail.receive(argThat(token -> "forged".equals(token)), org.mockito.ArgumentMatchers.any()))
                .thenThrow(new ApiException(ApiErrorCode.INBOUND_LINK_INVALID,
                        "This inbound address is not valid or has been retired"));

        mvc.perform(post("/api/v1/inbound/mail/forged")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"MessageID\":\"<abc@mail>\",\"TextBody\":\"Hello\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("INBOUND_LINK_INVALID"));
    }

    @Test
    void theAcknowledgementNamesNoAccountAndNoLetter() throws Exception {
        String body = mvc.perform(post("/api/v1/inbound/mail/abc.def")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"MessageID\":\"<abc@mail>\",\"TextBody\":\"Hello\"}"))
                .andReturn().getResponse().getContentAsString();

        assertThat(body).doesNotContain(ALICE.toString()).doesNotContain("<abc@mail>");
    }

    private static InboundMailItem item(UUID applicationId) {
        OffsetDateTime now = OffsetDateTime.now();
        return new InboundMailItem(MAIL, "ada@example.com", "Your interview", "Let's talk.",
                "interview", "Acme", "Backend Engineer", "interview", applicationId,
                "Backend Engineer", now, now);
    }

    @Test
    void theRepliesPageIsTheAccountsLettersAndAsksForTheFirstPage() throws Exception {
        when(replies.list(argThat(ALICE::equals), any(), any(), any(), eq(false)))
                .thenReturn(PageDTO.of(List.of(item(APP)), 1, 0, 50));

        mvc.perform(get("/api/v1/inbound/mails"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].id").value(MAIL.toString()))
                .andExpect(jsonPath("$.data.items[0].applicationId").value(APP.toString()))
                .andExpect(jsonPath("$.data.items[0].suggestedStage").value("interview"))
                .andExpect(jsonPath("$.data.total").value(1));

        verify(replies).list(argThat(ALICE::equals), argThat(pageable ->
                pageable.getPageNumber() == 0 && pageable.getPageSize() == 50), isNull(), isNull(), eq(false));
        verifyNoInteractions(mail);
    }

    @Test
    void aSearchTravelsToTheServiceAsTheReaderTypedIt() throws Exception {
        // The page owns the words, the service trims and lowercases them; this route only has
        // to carry the box across, including its spaces, so the two never disagree about what
        // was asked.
        when(replies.list(argThat(ALICE::equals), any(), eq("Acme"), isNull(), eq(false)))
                .thenReturn(PageDTO.of(List.of(item(APP)), 1, 0, 50));

        mvc.perform(get("/api/v1/inbound/mails").param("q", "Acme"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(1));

        verify(replies).list(argThat(ALICE::equals), any(Pageable.class), eq("Acme"), isNull(), eq(false));
    }

    @Test
    void theChipNumbersTravelWithTheSameSearch() throws Exception {
        // The numbers and the list are two answers to one question: the route carries `q` and
        // nothing else -- the picked reading is not sent, because each chip counts what it
        // would show rather than the one already showing.
        when(replies.intentCounts(argThat(ALICE::equals), eq("Acme"), eq(false)))
                .thenReturn(new IntentCounts(List.of(new IntentCount("unread", 2L)), 2L));

        mvc.perform(get("/api/v1/inbound/mails/intents").param("q", "Acme"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].intent").value("unread"))
                .andExpect(jsonPath("$.data.items[0].count").value(2))
                .andExpect(jsonPath("$.data.unfiled").value(2));

        verify(replies).intentCounts(argThat(ALICE::equals), eq("Acme"), eq(false));
    }

    @Test
    void aReadingChipTravelsToTheServiceAsTheReaderPickedIt() throws Exception {
        // The chip is the page's word; this route carries it unchanged beside the search, and
        // the service is the only place that decides which words are readings.
        when(replies.list(argThat(ALICE::equals), any(), eq("Acme"), eq("rejection"), eq(false)))
                .thenReturn(PageDTO.of(List.of(item(APP)), 1, 0, 50));

        mvc.perform(get("/api/v1/inbound/mails").param("q", "Acme").param("intent", "rejection"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(1));

        verify(replies).list(argThat(ALICE::equals), any(Pageable.class), eq("Acme"), eq("rejection"), eq(false));
    }

    @Test
    void theWaitingSwitchTravelsToTheService() throws Exception {
        // The switch is the page's question, not a filter this route invents: it rides
        // beside the words and the reading, and the service is the only place that reads it.
        when(replies.list(argThat(ALICE::equals), any(), any(), any(), eq(true)))
                .thenReturn(PageDTO.of(List.of(item(APP)), 1, 0, 50));

        mvc.perform(get("/api/v1/inbound/mails").param("unfiled", "true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.total").value(1));

        verify(replies).list(argThat(ALICE::equals), any(Pageable.class), isNull(), isNull(),
                eq(true));
    }

    @Test
    void theWaitingNumberTravelsWithTheChipCounts() throws Exception {
        // The answer carries the pile's own size even before the switch is pressed; the
        // route only has to carry the flag and the number across.
        when(replies.intentCounts(argThat(ALICE::equals), eq("Acme"), eq(true)))
                .thenReturn(new IntentCounts(List.of(new IntentCount("unread", 1L)), 1L));

        mvc.perform(get("/api/v1/inbound/mails/intents").param("q", "Acme")
                        .param("unfiled", "true"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unfiled").value(1));

        verify(replies).intentCounts(argThat(ALICE::equals), eq("Acme"), eq(true));
    }

    @Test
    void theReaderFilesOneLetterOnTheCardItAnswers() throws Exception {
        when(replies.file(ALICE, MAIL, APP)).thenReturn(item(APP));

        mvc.perform(post("/api/v1/inbound/mails/{id}/file", MAIL)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"applicationId\":\"" + APP + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applicationId").value(APP.toString()))
                .andExpect(jsonPath("$.data.filedAt").exists());

        verify(replies).file(ALICE, MAIL, APP);
        verifyNoInteractions(mail);
    }

    @Test
    void aLetterThatIsNotTheAccountsIsTheSame404WhetherItNeverExisted() throws Exception {
        when(replies.file(ALICE, MAIL, APP))
                .thenThrow(new ApiException(ApiErrorCode.INBOUND_MAIL_NOT_FOUND, "Reply not found"));

        mvc.perform(post("/api/v1/inbound/mails/{id}/file", MAIL)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"applicationId\":\"" + APP + "\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("INBOUND_MAIL_NOT_FOUND"));
    }

    @Test
    void aLetterAlreadyFiledElsewhereIsRefusedRatherThanMoved() throws Exception {
        when(replies.file(ALICE, MAIL, APP))
                .thenThrow(new ApiException(ApiErrorCode.INBOUND_MAIL_ALREADY_FILED,
                        "This reply is already filed on another application"));

        mvc.perform(post("/api/v1/inbound/mails/{id}/file", MAIL)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"applicationId\":\"" + APP + "\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("INBOUND_MAIL_ALREADY_FILED"));
    }

    @Test
    void filingWithNoApplicationIsRefusedBeforeTheService() throws Exception {
        mvc.perform(post("/api/v1/inbound/mails/{id}/file", MAIL)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));

        verifyNoInteractions(replies);
    }
}
