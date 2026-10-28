package com.careeros.auth.service;

import com.careeros.auth.dto.EmailChangeRequest;
import com.careeros.auth.entity.EmailChangeToken;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.EmailChangeTokenRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Moves the login address of a signed-in account (roadmap 26.1). Two letters leave when the
 * owner asks: a confirmation link to the address being claimed and a heads-up to the address
 * on the account, so a reader who did not ask learns that someone holds their password. The
 * move itself only happens when the new mailbox answers, which is the only proof that the
 * reader can receive mail there; a reset letter could otherwise be redirected to a stranger's
 * inbox. The token lives two hours -- shorter than a working day, longer than a reset link,
 * because the reader may have to reach a second mailbox to answer it.
 */
@Service
public class EmailChangeService {

    private static final Logger log = LoggerFactory.getLogger(EmailChangeService.class);
    private static final Duration CHANGE_TTL = Duration.ofHours(2);

    private final UserRepository users;
    private final EmailChangeTokenRepository changeTokens;
    private final TokenService tokenService;
    private final PasswordEncoder passwordEncoder;
    private final EmailSender emailSender;
    private final String webBaseUrl;

    public EmailChangeService(UserRepository users, EmailChangeTokenRepository changeTokens,
                              TokenService tokenService, PasswordEncoder passwordEncoder,
                              EmailSender emailSender,
                              @Value("${app.web.base-url:http://localhost:3000}") String webBaseUrl) {
        this.users = users;
        this.changeTokens = changeTokens;
        this.tokenService = tokenService;
        this.passwordEncoder = passwordEncoder;
        this.emailSender = emailSender;
        this.webBaseUrl = webBaseUrl.endsWith("/") ? webBaseUrl.substring(0, webBaseUrl.length() - 1) : webBaseUrl;
    }

    @Transactional
    public void request(UUID userId, EmailChangeRequest request) {
        User user = users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.USER_NOT_FOUND, "User not found"));
        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Password is incorrect");
        }
        String newEmail = request.newEmail().trim();
        if (newEmail.equalsIgnoreCase(user.getEmail())) {
            throw new ApiException(ApiErrorCode.EMAIL_UNCHANGED, "That is already the account's address");
        }
        if (users.existsByEmail(newEmail)) {
            throw new ApiException(ApiErrorCode.EMAIL_ALREADY_REGISTERED, "Email is already registered");
        }
        // One pending move per account: asking again replaces the earlier link.
        changeTokens.deleteByUserId(userId);
        String rawToken = TokenHasher.generateOpaqueToken();
        EmailChangeToken token = new EmailChangeToken();
        token.setUserId(userId);
        token.setTokenHash(TokenHasher.sha256Hex(rawToken));
        token.setNewEmail(newEmail);
        token.setExpiresAt(OffsetDateTime.now().plus(CHANGE_TTL));
        changeTokens.save(token);

        String link = webBaseUrl + "/confirm-email?token=" + rawToken;
        emailSender.send(newEmail, "Confirm your new AI Career OS address",
                "Confirm the move to this address within 2 hours by opening this link:\n\n" + link
                        + "\n\nIf the link is unreadable, paste this token into the confirmation screen:\n"
                        + rawToken
                        + "\n\nIf you did not ask for this, ignore this letter -- nothing changes"
                        + " until it is confirmed.");
        emailSender.send(user.getEmail(), "Your AI Career OS address is about to move",
                "Someone signed in to your account and asked to move its address to "
                        + newEmail + ".\n\nNothing has changed yet: the move only happens if that"
                        + " mailbox confirms within 2 hours.\n\nIf this was not you, change your"
                        + " password now -- that signs every other session out.");
    }

    /**
     * The new mailbox's answer. A token that is unknown, spent, expired or whose account has
     * since been erased is one refusal, so the public route cannot be used to probe which
     * links were real. An address taken by another account in the meantime marks the link
     * spent and refuses; the owner is free to ask again for a different one.
     */
    @Transactional(noRollbackFor = ApiException.class)
    public void confirm(String rawToken) {
        EmailChangeToken token = changeTokens.findByTokenHash(TokenHasher.sha256Hex(rawToken))
                .orElseThrow(() -> new ApiException(ApiErrorCode.EMAIL_CHANGE_INVALID,
                        "Invalid email change token"));
        OffsetDateTime now = OffsetDateTime.now();
        if (token.getUsedAt() != null || token.getExpiresAt().isBefore(now)) {
            throw new ApiException(ApiErrorCode.EMAIL_CHANGE_INVALID, "Email change token used or expired");
        }
        User user = users.findById(token.getUserId())
                .orElseThrow(() -> new ApiException(ApiErrorCode.EMAIL_CHANGE_INVALID,
                        "Invalid email change token"));
        token.setUsedAt(now);
        changeTokens.save(token);
        if (users.existsByEmail(token.getNewEmail())) {
            throw new ApiException(ApiErrorCode.EMAIL_ALREADY_REGISTERED, "Email is already registered");
        }

        String oldEmail = user.getEmail();
        String newEmail = token.getNewEmail();
        user.setEmail(newEmail);
        users.save(user);
        // The mailbox that receives reset links changed, so every open session signs out.
        tokenService.revokeAllForUser(user.getId());
        emailSender.send(newEmail, "Your AI Career OS sign-in address has moved",
                "This address is now the sign-in address of your AI Career OS account.\n\n"
                        + "Every other session was signed out. Sign in again with this address"
                        + " and your existing password.");
        emailSender.send(oldEmail, "Your AI Career OS sign-in address has moved",
                "The account's sign-in address was changed to " + newEmail + " after that mailbox"
                        + " confirmed the move.\n\nThis address no longer signs in. If you did not"
                        + " make this change, contact support before signing up again.");
        log.info("Email changed for user {}", user.getId());
    }
}
