package com.careeros.auth.service;

import com.careeros.auth.dto.LoginRequest;
import com.careeros.auth.dto.PasswordChangeRequest;
import com.careeros.auth.dto.RegisterRequest;
import com.careeros.auth.dto.ResetPasswordRequest;
import com.careeros.auth.entity.PasswordResetToken;
import com.careeros.auth.entity.User;
import com.careeros.auth.entity.UserProfile;
import com.careeros.auth.repository.PasswordResetTokenRepository;
import com.careeros.auth.repository.UserProfileRepository;
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

@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);
    private static final Duration RESET_TOKEN_TTL = Duration.ofMinutes(30);

    private final UserRepository users;
    private final UserProfileRepository profiles;
    private final PasswordResetTokenRepository resetTokens;
    private final TokenService tokenService;
    private final PasswordEncoder passwordEncoder;
    private final EmailSender emailSender;

    /**
     * Where the browser app is served, so the reset mail can carry a link the user can click
     * rather than an opaque token they would have to hand-carry to a screen that only reads it
     * out of the URL. `app.web.base-url` defaults to the same origin CORS already trusts.
     */
    private final String webBaseUrl;

    public AuthService(UserRepository users, UserProfileRepository profiles,
                       PasswordResetTokenRepository resetTokens, TokenService tokenService,
                       PasswordEncoder passwordEncoder, EmailSender emailSender,
                       @Value("${app.web.base-url:http://localhost:3000}") String webBaseUrl) {
        this.users = users;
        this.profiles = profiles;
        this.resetTokens = resetTokens;
        this.tokenService = tokenService;
        this.passwordEncoder = passwordEncoder;
        this.emailSender = emailSender;
        this.webBaseUrl = webBaseUrl.endsWith("/") ? webBaseUrl.substring(0, webBaseUrl.length() - 1) : webBaseUrl;
    }

    @Transactional
    public User register(RegisterRequest request) {
        if (users.existsByEmail(request.email())) {
            throw new ApiException(ApiErrorCode.EMAIL_ALREADY_REGISTERED, "Email is already registered");
        }
        User user = new User();
        user.setEmail(request.email().trim());
        user.setPasswordHash(passwordEncoder.encode(request.password()));
        user.setDisplayName(request.displayName().trim());
        users.save(user);

        UserProfile profile = new UserProfile();
        profile.setUserId(user.getId());
        profiles.save(profile);
        return user;
    }

    @Transactional(readOnly = true)
    public User login(LoginRequest request) {
        User user = users.findByEmail(request.email().trim())
                .filter(u -> passwordEncoder.matches(request.password(), u.getPasswordHash()))
                .orElseThrow(() -> new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Invalid email or password"));
        if (!user.isActive()) {
            throw new ApiException(ApiErrorCode.USER_DISABLED, "Account is disabled");
        }
        return user;
    }

    /** Always succeeds — never reveal whether the email exists. */
    @Transactional
    public void forgotPassword(String email) {
        users.findByEmail(email.trim()).ifPresent(user -> {
            String rawToken = TokenHasher.generateOpaqueToken();
            PasswordResetToken token = new PasswordResetToken();
            token.setUserId(user.getId());
            token.setTokenHash(TokenHasher.sha256Hex(rawToken));
            token.setExpiresAt(OffsetDateTime.now().plus(RESET_TOKEN_TTL));
            resetTokens.save(token);
            String resetLink = webBaseUrl + "/reset-password?token=" + rawToken;
            emailSender.send(user.getEmail(), "Reset your AI Career OS password",
                    "Choose a new password within 30 minutes by opening this link:\n\n" + resetLink
                            + "\n\nIf the link is unreadable, paste this token into the reset screen:\n"
                            + rawToken);
        });
    }

    @Transactional(noRollbackFor = ApiException.class)
    public void resetPassword(ResetPasswordRequest request) {
        PasswordResetToken token = resetTokens.findByTokenHash(TokenHasher.sha256Hex(request.token()))
                .orElseThrow(() -> new ApiException(ApiErrorCode.RESET_TOKEN_INVALID, "Invalid reset token"));
        OffsetDateTime now = OffsetDateTime.now();
        if (token.getUsedAt() != null || token.getExpiresAt().isBefore(now)) {
            throw new ApiException(ApiErrorCode.RESET_TOKEN_INVALID, "Reset token used or expired");
        }
        User user = users.findById(token.getUserId())
                .orElseThrow(() -> new ApiException(ApiErrorCode.RESET_TOKEN_OWNER_NOT_FOUND, "Invalid reset token"));
        token.setUsedAt(now);
        resetTokens.save(token);
        user.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        users.save(user);
        // Force re-login everywhere after a password change.
        tokenService.revokeAllForUser(user.getId());
        log.info("Password reset for user {}", user.getId());
    }

    /**
     * Replaces the password of a signed-in account (roadmap 24.1). The current password is the
     * re-authentication: an open tab, a borrowed laptop or a stolen access token is not enough
     * to take the account away from its owner. Every refresh token is revoked afterwards, the
     * same response the reset path gives, so a reader who suspects a compromise leaves every
     * other session behind; the access token already in this reader's hand dies at its short
     * expiry like it always does.
     */
    @Transactional
    public void changePassword(UUID userId, PasswordChangeRequest request) {
        User user = users.findById(userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.USER_NOT_FOUND, "User not found"));
        if (!passwordEncoder.matches(request.currentPassword(), user.getPasswordHash())) {
            throw new ApiException(ApiErrorCode.INVALID_CREDENTIALS, "Current password is incorrect");
        }
        if (passwordEncoder.matches(request.newPassword(), user.getPasswordHash())) {
            throw new ApiException(ApiErrorCode.PASSWORD_UNCHANGED,
                    "New password must differ from the current one");
        }
        user.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        users.save(user);
        tokenService.revokeAllForUser(userId);
        log.info("Password changed for user {}", userId);
    }
}
