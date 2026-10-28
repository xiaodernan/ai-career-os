package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.careeros.auth.dto.EmailChangeRequest;
import com.careeros.auth.entity.EmailChangeToken;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.EmailChangeTokenRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * Moving the account's login address (roadmap 26).
 *
 * <p>The move has two halves and each is pinned here. Asking costs the password -- a borrowed
 * tab is not enough -- refuses the address the account already has, refuses one another
 * account owns, and sends the confirmation link to the mailbox being claimed while warning
 * the old mailbox that someone asked. Answering costs the token: the address moves, every
 * other session signs out, both mailboxes hear the outcome, and a link that is unknown,
 * spent, expired, ownerless or overtaken by a registration is refused. The hashed token is
 * what the database keeps, so a leaked table cannot confirm a move.
 */
class EmailChangeServiceTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String PASSWORD = "Str0ngPassphrase!23";
    private static final String OLD_EMAIL = "ada@example.invalid";
    private static final String NEW_EMAIL = "ada.new@example.invalid";
    private static final Pattern TOKEN_IN_LINK =
            Pattern.compile("/confirm-email\\?token=([A-Za-z0-9_-]{43})");

    private final PasswordEncoder encoder = new BCryptPasswordEncoder(4);
    private UserRepository users;
    private EmailChangeTokenRepository changeTokens;
    private TokenService tokenService;
    private EmailSender emailSender;
    private EmailChangeService service;
    private User alice;

    @BeforeEach
    void setUp() {
        users = mock(UserRepository.class);
        changeTokens = mock(EmailChangeTokenRepository.class);
        tokenService = mock(TokenService.class);
        emailSender = mock(EmailSender.class);
        service = new EmailChangeService(users, changeTokens, tokenService, encoder, emailSender,
                "https://careeros.example/");

        alice = new User();
        alice.setId(ALICE);
        alice.setEmail(OLD_EMAIL);
        alice.setPasswordHash(encoder.encode(PASSWORD));
        when(users.findById(ALICE)).thenReturn(Optional.of(alice));
    }

    @Test
    void askingMailsTheClaimedMailboxALinkAndWarnsTheOldOne() {
        service.request(ALICE, new EmailChangeRequest(PASSWORD, "  " + NEW_EMAIL + " "));

        ArgumentCaptor<EmailChangeToken> stored = ArgumentCaptor.forClass(EmailChangeToken.class);
        verify(changeTokens).save(stored.capture());
        EmailChangeToken pending = stored.getValue();
        assertThat(pending.getUserId()).isEqualTo(ALICE);
        assertThat(pending.getNewEmail()).isEqualTo(NEW_EMAIL);
        // The window outlasts a reset link and still fits inside a working afternoon.
        assertThat(pending.getExpiresAt()).isAfter(OffsetDateTime.now().plusHours(1));
        assertThat(pending.getExpiresAt()).isBefore(OffsetDateTime.now().plusHours(3));
        assertThat(pending.getUsedAt()).isNull();

        ArgumentCaptor<String> to = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> body = ArgumentCaptor.forClass(String.class);
        verify(emailSender, times(2)).send(to.capture(), anyString(), body.capture());
        // The link goes to the mailbox being claimed; the warning to the mailbox on the account.
        assertThat(to.getAllValues()).containsExactly(NEW_EMAIL, OLD_EMAIL);
        Matcher link = TOKEN_IN_LINK.matcher(body.getAllValues().get(0));
        assertThat(link.find()).isTrue();
        String rawToken = link.group(1);
        // Only a hash is kept, so a stolen table cannot answer the letter.
        assertThat(pending.getTokenHash()).isEqualTo(TokenHasher.sha256Hex(rawToken));
        assertThat(pending.getTokenHash()).isNotEqualTo(rawToken);
        assertThat(body.getAllValues().get(1)).contains(NEW_EMAIL);
    }

    @Test
    void askingAgainReplacesTheEarlierLinkInsteadOfLeavingTwoLive() {
        service.request(ALICE, new EmailChangeRequest(PASSWORD, NEW_EMAIL));

        verify(changeTokens).deleteByUserId(ALICE);
        verify(changeTokens).save(any());
    }

    @Test
    void aWrongPasswordShowsNoLetterAndStoresNothing() {
        assertThatThrownBy(() -> service.request(ALICE, new EmailChangeRequest("not-it-99", NEW_EMAIL)))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.code()).isEqualTo(ApiErrorCode.INVALID_CREDENTIALS);
                    assertThat(e.getMessage()).isEqualTo("Password is incorrect");
                });

        verifyNoInteractions(changeTokens);
        verifyNoInteractions(emailSender);
    }

    @Test
    void theAddressTheAccountAlreadyHasIsRefusedHoweverItIsCased() {
        assertThatThrownBy(() -> service.request(ALICE, new EmailChangeRequest(PASSWORD, "  ADA@Example.Invalid ")))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_UNCHANGED));

        verifyNoInteractions(changeTokens);
        verifyNoInteractions(emailSender);
    }

    @Test
    void anAddressAnotherAccountOwnsIsRefusedBeforeAnyLetter() {
        when(users.existsByEmail(NEW_EMAIL)).thenReturn(true);

        assertThatThrownBy(() -> service.request(ALICE, new EmailChangeRequest(PASSWORD, NEW_EMAIL)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_ALREADY_REGISTERED));

        verify(changeTokens, never()).save(any());
        verifyNoInteractions(emailSender);
    }

    @Test
    void answeringMovesTheAddressSpendsTheLinkAndSignsEveryOtherSessionOut() {
        String rawToken = TokenHasher.generateOpaqueToken();
        EmailChangeToken token = pending(rawToken);
        when(changeTokens.findByTokenHash(TokenHasher.sha256Hex(rawToken))).thenReturn(Optional.of(token));

        service.confirm(rawToken);

        assertThat(alice.getEmail()).isEqualTo(NEW_EMAIL);
        verify(users).save(alice);
        assertThat(token.getUsedAt()).isNotNull();
        verify(changeTokens).save(token);
        verify(tokenService).revokeAllForUser(ALICE);

        ArgumentCaptor<String> to = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> body = ArgumentCaptor.forClass(String.class);
        verify(emailSender, times(2)).send(to.capture(), anyString(), body.capture());
        assertThat(to.getAllValues()).containsExactly(NEW_EMAIL, OLD_EMAIL);
        assertThat(body.getAllValues().get(1)).contains(NEW_EMAIL);
    }

    @Test
    void aLinkNobodyIssuedIsOneRefusalWithNothingTouched() {
        when(changeTokens.findByTokenHash(anyString())).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.confirm("not-a-real-token"))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_CHANGE_INVALID));

        verify(users, never()).save(any());
        verifyNoInteractions(tokenService);
        verifyNoInteractions(emailSender);
    }

    @Test
    void aSpentOrExpiredLinkIsTheSameRefusalEvenWhenTheHashMatches() {
        String spentRaw = TokenHasher.generateOpaqueToken();
        EmailChangeToken spent = pending(spentRaw);
        spent.setUsedAt(OffsetDateTime.now().minusMinutes(1));
        when(changeTokens.findByTokenHash(TokenHasher.sha256Hex(spentRaw))).thenReturn(Optional.of(spent));

        assertThatThrownBy(() -> service.confirm(spentRaw))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_CHANGE_INVALID));

        String expiredRaw = TokenHasher.generateOpaqueToken();
        EmailChangeToken expired = pending(expiredRaw);
        expired.setExpiresAt(OffsetDateTime.now().minusMinutes(1));
        when(changeTokens.findByTokenHash(TokenHasher.sha256Hex(expiredRaw))).thenReturn(Optional.of(expired));

        assertThatThrownBy(() -> service.confirm(expiredRaw))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_CHANGE_INVALID));

        assertThat(alice.getEmail()).isEqualTo(OLD_EMAIL);
        verify(users, never()).save(any());
        verifyNoInteractions(tokenService);
    }

    @Test
    void aLinkWhoseAccountWasErasedIsTheSameRefusal() {
        String rawToken = TokenHasher.generateOpaqueToken();
        when(changeTokens.findByTokenHash(TokenHasher.sha256Hex(rawToken)))
                .thenReturn(Optional.of(pending(rawToken)));
        when(users.findById(ALICE)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.confirm(rawToken))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_CHANGE_INVALID));

        verify(users, never()).save(any());
        verifyNoInteractions(tokenService);
    }

    @Test
    void anAddressRegisteredMeanwhileIsRefusedAndTheLinkIsBurned() {
        String rawToken = TokenHasher.generateOpaqueToken();
        EmailChangeToken token = pending(rawToken);
        when(changeTokens.findByTokenHash(TokenHasher.sha256Hex(rawToken))).thenReturn(Optional.of(token));
        when(users.existsByEmail(NEW_EMAIL)).thenReturn(true);

        assertThatThrownBy(() -> service.confirm(rawToken))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.EMAIL_ALREADY_REGISTERED));

        // Spent on the way out: the same link cannot be retried at the address it lost.
        assertThat(token.getUsedAt()).isNotNull();
        verify(changeTokens).save(token);
        assertThat(alice.getEmail()).isEqualTo(OLD_EMAIL);
        verify(users, never()).save(any());
        verifyNoInteractions(tokenService);
        verifyNoInteractions(emailSender);
    }

    private EmailChangeToken pending(String rawToken) {
        EmailChangeToken token = new EmailChangeToken();
        token.setUserId(ALICE);
        token.setTokenHash(TokenHasher.sha256Hex(rawToken));
        token.setNewEmail(NEW_EMAIL);
        token.setExpiresAt(OffsetDateTime.now().plusHours(1));
        return token;
    }
}
