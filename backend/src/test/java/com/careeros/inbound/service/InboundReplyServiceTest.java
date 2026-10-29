package com.careeros.inbound.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.inbound.dto.InboundMailDtos.InboundMailItem;
import com.careeros.inbound.entity.InboundMail;
import com.careeros.inbound.repository.InboundMailRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The reply meets the application (roadmap 37.3).
 *
 * <p>The claims are about restraint. The match is the employer's name and, when the reader has
 * several applications there, the letter's role narrowing to exactly one title -- a match that
 * is merely plausible files nothing, because a reply on the wrong card is worse than a reply
 * waiting. Filing writes two rows in one transaction: the letter names the card, and the card's
 * timeline gains a reply event that says what the recruiter wrote. A letter is filed once: the
 * same card again is a no-op, and a different card is refused rather than moved, because the
 * first card's timeline already says this letter answers it. Nothing here moves the
 * application's stage; a reading only suggests one.
 */
class InboundReplyServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID APP = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID APP2 = UUID.fromString("33333333-3333-4333-8333-333333333333");
    private static final UUID MAIL = UUID.fromString("44444444-4444-4444-8444-444444444444");

    private final InboundMailRepository mails = mock(InboundMailRepository.class);
    private final ApplicationRepository applications = mock(ApplicationRepository.class);
    private final ApplicationEventRepository events = mock(ApplicationEventRepository.class);
    private final InboundReplyService service = new InboundReplyService(mails, applications, events);

    private static InboundMail mail(String company, String role) {
        InboundMail mail = new InboundMail();
        ReflectionTestUtils.setField(mail, "id", MAIL);
        mail.setUserId(ALICE);
        mail.setFromAddress("ada@example.com");
        mail.setSubject("Your interview");
        mail.setBodyText("Let's schedule a call.");
        mail.setIntent("interview");
        mail.setCompany(company);
        mail.setRole(role);
        mail.setReceivedAt(OffsetDateTime.now());
        return mail;
    }

    private static Application application(UUID id, String title, String company) {
        Application app = new Application();
        ReflectionTestUtils.setField(app, "id", id);
        app.setUserId(ALICE);
        app.setTitle(title);
        app.setCompanyName(company);
        return app;
    }

    private ArgumentCaptor<ApplicationEvent> oneReplyEvent() {
        ArgumentCaptor<ApplicationEvent> captor = ArgumentCaptor.forClass(ApplicationEvent.class);
        verify(events).save(captor.capture());
        return captor;
    }

    @Test
    void aReadLetterIsFiledOnTheOneCardItsCompanyNamesAndTheCardHearsOfIt() {
        InboundMail mail = mail("Acme", "Backend Engineer");
        when(applications.findByUserIdAndCompanyNameIgnoreCase(ALICE, "Acme"))
                .thenReturn(List.of(application(APP, "Backend Engineer", "Acme")));

        assertThat(service.autoFile(mail)).isTrue();

        assertThat(mail.getApplicationId()).isEqualTo(APP);
        assertThat(mail.getFiledAt()).isNotNull();
        verify(mails).save(mail);
        ApplicationEvent event = oneReplyEvent().getValue();
        assertThat(event.getKind()).isEqualTo(InboundReplyService.EVENT_REPLY);
        assertThat(event.getApplicationId()).isEqualTo(APP);
        assertThat(event.getUserId()).isEqualTo(ALICE);
        assertThat(event.getPayload())
                .containsEntry("mail_id", MAIL.toString())
                .containsEntry("sender", "ada@example.com")
                .containsEntry("subject", "Your interview")
                .containsEntry("intent", "interview");
    }

    @Test
    void severalApplicationsAtOneEmployerAreNarrowedByTheRoleTheLetterNames() {
        InboundMail mail = mail("Acme", "backend");
        when(applications.findByUserIdAndCompanyNameIgnoreCase(ALICE, "Acme")).thenReturn(List.of(
                application(APP, "Backend Engineer", "Acme"),
                application(APP2, "Data Analyst", "Acme")));

        assertThat(service.autoFile(mail)).isTrue();
        assertThat(mail.getApplicationId()).isEqualTo(APP);
    }

    @Test
    void aRoleThatNarrowsToNothingFilesNothing() {
        InboundMail mail = mail("Acme", "Product Manager");
        when(applications.findByUserIdAndCompanyNameIgnoreCase(ALICE, "Acme")).thenReturn(List.of(
                application(APP, "Backend Engineer", "Acme"),
                application(APP2, "Data Analyst", "Acme")));

        assertThat(service.autoFile(mail)).isFalse();
        assertThat(mail.getApplicationId()).isNull();
        verify(mails, never()).save(any());
        verify(events, never()).save(any());
    }

    @Test
    void aRoleThatNarrowsToTwoCardsFilesNothing() {
        InboundMail mail = mail("Acme", "Engineer");
        when(applications.findByUserIdAndCompanyNameIgnoreCase(ALICE, "Acme")).thenReturn(List.of(
                application(APP, "Engineer", "Acme"),
                application(APP2, "Senior Engineer", "Acme")));

        assertThat(service.autoFile(mail)).isFalse();
        verify(mails, never()).save(any());
    }

    @Test
    void aLetterWithNoEmployerReadsIsNotFiled() {
        assertThat(service.autoFile(mail(" ", "Backend Engineer"))).isFalse();
        assertThat(service.autoFile(mail(null, "Backend Engineer"))).isFalse();
        assertThat(service.autoFile(null)).isFalse();
        verifyNoInteractions(applications, mails, events);
    }

    @Test
    void aLetterAlreadyFiledIsNotFiledAgain() {
        InboundMail mail = mail("Acme", "Backend Engineer");
        mail.setApplicationId(APP);

        assertThat(service.autoFile(mail)).isFalse();
        verifyNoInteractions(applications, mails, events);
    }

    @Test
    void theReaderFilesAWaitingLetterAndTheCardGainsAReplyEvent() {
        InboundMail mail = mail("Acme", "Backend Engineer");
        Application app = application(APP, "Backend Engineer", "Acme");
        when(mails.findByIdAndUserId(MAIL, ALICE)).thenReturn(Optional.of(mail));
        when(applications.findByIdAndUserId(APP, ALICE)).thenReturn(Optional.of(app));

        InboundMailItem item = service.file(ALICE, MAIL, APP);

        assertThat(item.id()).isEqualTo(MAIL);
        assertThat(item.applicationId()).isEqualTo(APP);
        assertThat(item.applicationTitle()).isEqualTo("Backend Engineer");
        assertThat(item.suggestedStage()).isEqualTo("interview");
        assertThat(item.filedAt()).isNotNull();
        assertThat(oneReplyEvent().getValue().getPayload()).containsEntry("mail_id", MAIL.toString());
    }

    @Test
    void filingOnTheSameCardTwiceChangesNothing() {
        InboundMail mail = mail("Acme", "Backend Engineer");
        mail.setApplicationId(APP);
        mail.setFiledAt(OffsetDateTime.now().minusHours(1));
        when(mails.findByIdAndUserId(MAIL, ALICE)).thenReturn(Optional.of(mail));
        when(applications.findByIdAndUserId(APP, ALICE))
                .thenReturn(Optional.of(application(APP, "Backend Engineer", "Acme")));

        InboundMailItem item = service.file(ALICE, MAIL, APP);

        assertThat(item.applicationId()).isEqualTo(APP);
        verify(mails, never()).save(any());
        verifyNoInteractions(events);
    }

    @Test
    void filingOnADifferentCardIsRefusedRatherThanMoved() {
        InboundMail mail = mail("Acme", "Backend Engineer");
        mail.setApplicationId(APP);
        when(mails.findByIdAndUserId(MAIL, ALICE)).thenReturn(Optional.of(mail));
        when(applications.findByIdAndUserId(APP2, ALICE))
                .thenReturn(Optional.of(application(APP2, "Data Analyst", "Acme")));

        assertThatThrownBy(() -> service.file(ALICE, MAIL, APP2))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INBOUND_MAIL_ALREADY_FILED));
        verify(mails, never()).save(any());
        verifyNoInteractions(events);
    }

    @Test
    void aLetterThatIsNotTheAccountsIsTheSame404WhetherItNeverExisted() {
        when(mails.findByIdAndUserId(MAIL, ALICE)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.file(ALICE, MAIL, APP))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INBOUND_MAIL_NOT_FOUND));
        verifyNoInteractions(applications, events);
    }

    @Test
    void anApplicationThatIsNotTheAccountsIsNotFound() {
        when(mails.findByIdAndUserId(MAIL, ALICE)).thenReturn(Optional.of(mail("Acme", null)));
        when(applications.findByIdAndUserId(APP, ALICE)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.file(ALICE, MAIL, APP))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.APPLICATION_NOT_FOUND));
        verify(mails, never()).save(any());
        verifyNoInteractions(events);
    }

    @Test
    void aReadingSuggestsAStageInTheBoardsOwnVocabularyAndOnlyForThree() {
        assertThat(InboundReplyService.suggestedStage("rejection")).isEqualTo("rejected");
        assertThat(InboundReplyService.suggestedStage("interview")).isEqualTo("interview");
        assertThat(InboundReplyService.suggestedStage("offer")).isEqualTo("offer");
        assertThat(InboundReplyService.suggestedStage("info")).isNull();
        assertThat(InboundReplyService.suggestedStage("other")).isNull();
        assertThat(InboundReplyService.suggestedStage(null)).isNull();
    }

    @Test
    void thePageCarriesEachLettersCardAndSuggestionAndLeavesWaitingOnesUnnamed() {
        InboundMail filed = mail("Acme", "Backend Engineer");
        filed.setApplicationId(APP);
        InboundMail waiting = mail("Globex", null);
        waiting.setIntent(null);
        ReflectionTestUtils.setField(waiting, "id", UUID.randomUUID());
        when(mails.findByUserIdOrderByReceivedAtDescIdDesc(eq(ALICE), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(filed, waiting), PageRequest.of(0, 50), 2));
        when(applications.findAllById(any())).thenReturn(List.of(
                application(APP, "Backend Engineer", "Acme")));

        PageDTO<InboundMailItem> page = service.list(ALICE, PageRequest.of(0, 50));

        assertThat(page.total()).isEqualTo(2);
        assertThat(page.page()).isZero();
        InboundMailItem first = page.items().get(0);
        assertThat(first.applicationTitle()).isEqualTo("Backend Engineer");
        assertThat(first.suggestedStage()).isEqualTo("interview");
        InboundMailItem second = page.items().get(1);
        assertThat(second.applicationId()).isNull();
        assertThat(second.applicationTitle()).isNull();
        assertThat(second.suggestedStage()).isNull();
    }
}
