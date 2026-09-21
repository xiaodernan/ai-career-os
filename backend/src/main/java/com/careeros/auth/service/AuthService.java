package com.careeros.auth.service;

import com.careeros.auth.dto.LoginRequest;
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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
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

    public AuthService(UserRepository users, UserProfileRepository profiles,
                       PasswordResetTokenRepository resetTokens, TokenService tokenService,
                       PasswordEncoder passwordEncoder, EmailSender emailSender) {
        this.users = users;
        this.profiles = profiles;
        this.resetTokens = resetTokens;
        this.tokenService = tokenService;
        this.passwordEncoder = passwordEncoder;
        this.emailSender = emailSender;
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
            emailSender.send(user.getEmail(), "Reset your AI Career OS password",
                    "Use this token within 30 minutes to reset your password: " + rawToken);
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
                .orElseThrow(() -> new ApiException(ApiErrorCode.RESET_TOKEN_INVALID, "Invalid reset token"));
        token.setUsedAt(now);
        resetTokens.save(token);
        user.setPasswordHash(passwordEncoder.encode(request.newPassword()));
        users.save(user);
        // Force re-login everywhere after a password change.
        tokenService.revokeAllForUser(user.getId());
        log.info("Password reset for user {}", user.getId());
    }
}
