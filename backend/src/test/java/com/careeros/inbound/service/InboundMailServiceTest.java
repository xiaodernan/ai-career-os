package com.careeros.inbound.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.auth.entity.User;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.inbound.entity.InboundMail;
import com.careeros.inbound.repository.InboundMailRepository;
import com.careeros.inbound.web.InboundMailPayload;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * What the webhook does with a forwarded letter (roadmap 37.1).
 *
 * <p>The caller is a provider, so the claims are about retries and rubbish: a delivered letter
 * is stored trimmed with its own date; the same MessageID twice is one row; a payload with no
 * id is deduplicated by a digest of what it said, and a changed body is a new letter; fields
 * are capped instead of refused, because the provider would retry a 400 forever; an empty
 * payload is acknowledged and dropped; an unreadable token and a deleted account are the same
 * 404; and a date this server cannot read -- or one forged into the future -- becomes the
 * moment the delivery arrived.
 */
class InboundMailServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String DOMAIN = "inbox.careeros.example";

    private final InboundLinks links = new InboundLinks("test-secret", DOMAIN);
    private final InboundMailRepository mails = mock(InboundMailRepository.class);
    private final UserRepository users = mock(UserRepository.class);
    private final InboundMailService service = new InboundMailService(links, mails, users);

    private String token() {
        return links.address(ALICE).split("@")[0];
    }

    private void accountExists() {
        User user = new User();
        user.setId(ALICE);
        when(users.findById(ALICE)).thenReturn(Optional.of(user));
        when(mails.findByUserIdAndMessageKey(any(), anyString())).thenReturn(Optional.empty());
    }

    private static InboundMailPayload payload(String messageId, String from, String subject, String body, String date) {
        return new InboundMailPayload(messageId, from, subject, body, date);
    }

    private InboundMail captured() {
        ArgumentCaptor<InboundMail> captor = ArgumentCaptor.forClass(InboundMail.class);
        verify(mails).save(captor.capture());
        return captor.getValue();
    }

    @Test
    void aLetterIsStoredTrimmedWithItsOwnDateAndItsAccount() {
        accountExists();

        service.receive(token(), payload("<abc@mail>", "  Ada <ada@example.com>  ",
                "  Your application  ", "  Hello, we would like to talk.  ",
                "2019-06-05T16:53:08-05:00"));

        InboundMail mail = captured();
        assertThat(mail.getUserId()).isEqualTo(ALICE);
        assertThat(mail.getMessageKey()).isEqualTo("<abc@mail>");
        assertThat(mail.getFromAddress()).isEqualTo("Ada <ada@example.com>");
        assertThat(mail.getSubject()).isEqualTo("Your application");
        assertThat(mail.getBodyText()).isEqualTo("Hello, we would like to talk.");
        assertThat(mail.getReceivedAt()).isEqualTo(OffsetDateTime.parse("2019-06-05T16:53:08-05:00"));
    }

    @Test
    void theSameMessageIdTwiceIsTheSameLetterAndNotASecondRow() {
        accountExists();
        InboundMail existing = new InboundMail();
        existing.setUserId(ALICE);
        existing.setMessageKey("<abc@mail>");
        when(mails.findByUserIdAndMessageKey(ALICE, "<abc@mail>")).thenReturn(Optional.of(existing));

        InboundMailService.Received received = service.receive(token(),
                payload("<abc@mail>", "ada@example.com", "Hi", "Hello", null));

        assertThat(received.duplicate()).isTrue();
        verify(mails, never()).save(any());
    }

    @Test
    void aPayloadWithNoIdIsDeduplicatedByWhatItSaidAndAChangedBodyIsANewLetter() {
        accountExists();
        AtomicReference<String> firstKey = new AtomicReference<>();
        when(mails.save(any())).thenAnswer(invocation -> {
            InboundMail mail = invocation.getArgument(0);
            firstKey.set(mail.getMessageKey());
            return mail;
        });

        service.receive(token(), payload(null, "ada@example.com", "Hi", "First reply", null));
        assertThat(firstKey.get()).matches("[0-9a-f]{64}");

        StringBuilder changed = new StringBuilder("First reply");
        changed.append(" and one more line");
        service.receive(token(), payload(null, "ada@example.com", "Hi", changed.toString(), null));

        ArgumentCaptor<InboundMail> captor = ArgumentCaptor.forClass(InboundMail.class);
        verify(mails, org.mockito.Mockito.times(2)).save(captor.capture());
        assertThat(captor.getAllValues().get(0).getMessageKey())
                .isNotEqualTo(captor.getAllValues().get(1).getMessageKey());
    }

    @Test
    void aBodyAndSubjectBeyondTheirCapsAreCutRatherThanRefused() {
        accountExists();

        service.receive(token(), payload("<abc@mail>", "ada@example.com",
                "s".repeat(600), "b".repeat(25_000), null));

        InboundMail mail = captured();
        assertThat(mail.getSubject()).hasSize(500);
        assertThat(mail.getBodyText()).hasSize(20_000);
    }

    @Test
    void aCapThatFallsOnASurrogatePairCutsThePairRatherThanHalfOfIt() {
        accountExists();
        String body = "a".repeat(19_999) + "\uD83D\uDE00";

        service.receive(token(), payload("<abc@mail>", "ada@example.com", "Hi", body, null));

        InboundMail mail = captured();
        assertThat(mail.getBodyText()).hasSize(19_999);
        assertThat(Character.isHighSurrogate(mail.getBodyText().charAt(19_998))).isFalse();
    }

    @Test
    void aPayloadWithNoLetterInItIsAcknowledgedWithoutARow() {
        accountExists();

        InboundMailService.Received received = service.receive(token(),
                payload("<abc@mail>", " ", null, "", null));

        assertThat(received.id()).isNull();
        assertThat(received.duplicate()).isFalse();
        verify(mails, never()).save(any());
    }

    @Test
    void aForgedTokenOrAnErasedAccountIsTheSame404() {
        assertThatThrownBy(() -> service.receive("forged",
                payload("<abc@mail>", "ada@example.com", "Hi", "Hello", null)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INBOUND_LINK_INVALID));

        String local = token();
        when(users.findById(ALICE)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.receive(local,
                payload("<abc@mail>", "ada@example.com", "Hi", "Hello", null)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.INBOUND_LINK_INVALID));
    }

    @Test
    void anUnreadableDateOrOneForgedIntoTheFutureBecomesTheArrivalMoment() {
        accountExists();
        OffsetDateTime before = OffsetDateTime.now().minusSeconds(1);

        service.receive(token(), payload("<one@mail>", "ada@example.com", "Hi", "Hello", "yesterday"));
        InboundMail unreadable = captured();
        assertThat(unreadable.getReceivedAt()).isAfterOrEqualTo(before);

        OffsetDateTime future = OffsetDateTime.now().plusDays(3);
        service.receive(token(), payload("<two@mail>", "ada@example.com", "Hi", "Hello", future.toString()));
        ArgumentCaptor<InboundMail> captor = ArgumentCaptor.forClass(InboundMail.class);
        verify(mails, org.mockito.Mockito.times(2)).save(captor.capture());
        assertThat(captor.getAllValues().get(1).getReceivedAt())
                .isBefore(future)
                .isAfter(before);
    }

    @Test
    void theRfcMailDateIsReadAsTheLettersDate() {
        accountExists();

        service.receive(token(), payload("<abc@mail>", "ada@example.com", "Hi", "Hello",
                "Wed, 5 Jun 2019 16:53:08 -0500"));

        assertThat(captured().getReceivedAt())
                .isEqualTo(OffsetDateTime.parse("2019-06-05T16:53:08-05:00"));
    }
}
