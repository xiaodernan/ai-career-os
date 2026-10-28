package com.careeros.auth.web;

import com.careeros.auth.dto.AuthResponse;
import com.careeros.auth.dto.AuthUserResponse;
import com.careeros.auth.dto.ConfirmEmailChangeRequest;
import com.careeros.auth.dto.ForgotPasswordRequest;
import com.careeros.auth.dto.LoginRequest;
import com.careeros.auth.dto.RefreshTokenRequest;
import com.careeros.auth.dto.RegisterRequest;
import com.careeros.auth.dto.ResetPasswordRequest;
import com.careeros.auth.dto.TokenPairResponse;
import com.careeros.auth.entity.User;
import com.careeros.auth.service.AuthService;
import com.careeros.auth.service.EmailChangeService;
import com.careeros.auth.service.TokenService;
import com.careeros.common.ClientInfo;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final TokenService tokenService;
    private final EmailChangeService emailChange;

    public AuthController(AuthService authService, TokenService tokenService,
                          EmailChangeService emailChange) {
        this.authService = authService;
        this.tokenService = tokenService;
        this.emailChange = emailChange;
    }

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public AuthResponse register(@RequestBody @Valid RegisterRequest request, HttpServletRequest http) {
        User user = authService.register(request);
        return new AuthResponse(AuthUserResponse.from(user),
                tokenService.issueForNewSession(user, ClientInfo.from(http)));
    }

    @PostMapping("/login")
    public AuthResponse login(@RequestBody @Valid LoginRequest request, HttpServletRequest http) {
        User user = authService.login(request);
        return new AuthResponse(AuthUserResponse.from(user),
                tokenService.issueForNewSession(user, ClientInfo.from(http)));
    }

    @PostMapping("/refresh")
    public TokenPairResponse refresh(@RequestBody @Valid RefreshTokenRequest request) {
        return tokenService.refresh(request.refreshToken());
    }

    @PostMapping("/logout")
    public Map<String, Object> logout(@RequestBody @Valid RefreshTokenRequest request) {
        tokenService.logout(request.refreshToken());
        return Map.of("loggedOut", true);
    }

    @PostMapping("/password/forgot")
    public Map<String, Object> forgot(@RequestBody @Valid ForgotPasswordRequest request) {
        authService.forgotPassword(request.email());
        return Map.of("accepted", true);
    }

    @PostMapping("/password/reset")
    public Map<String, Object> reset(@RequestBody @Valid ResetPasswordRequest request) {
        authService.resetPassword(request);
        return Map.of("reset", true);
    }

    /** Answered by the new mailbox; the token is the proof, so this route takes no session. */
    @PostMapping("/email-change/confirm")
    public Map<String, Object> confirmEmailChange(@RequestBody @Valid ConfirmEmailChangeRequest request) {
        emailChange.confirm(request.token());
        return Map.of("changed", true);
    }
}
