package com.careeros.auth.service;

import com.careeros.auth.dto.TokenPairResponse;
import com.careeros.auth.entity.RefreshToken;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.RefreshTokenRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.config.AppProperties;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Refresh-token lifecycle: issue, rotate, reuse-detect, revoke.
 * Rotation: each refresh revokes the presented token and issues a successor in the same family.
 * Reuse detection: presenting an already-revoked token revokes the entire family (forced re-login).
 */
@Service
public class TokenService {

    private final RefreshTokenRepository refreshTokens;
    private final UserRepository users;
    private final JwtService jwtService;
    private final Duration refreshTtl;

    public TokenService(RefreshTokenRepository refreshTokens, UserRepository users,
                        JwtService jwtService, AppProperties props) {
        this.refreshTokens = refreshTokens;
        this.users = users;
        this.jwtService = jwtService;
        this.refreshTtl = Duration.ofDays(props.getJwt().getRefreshTtlDays());
    }

    @Transactional
    public TokenPairResponse issueTokenPair(User user, UUID familyId) {
        String rawToken = TokenHasher.generateOpaqueToken();
        RefreshToken entity = new RefreshToken();
        entity.setUserId(user.getId());
        entity.setTokenHash(TokenHasher.sha256Hex(rawToken));
        entity.setFamilyId(familyId);
        entity.setExpiresAt(OffsetDateTime.now().plus(refreshTtl));
        refreshTokens.save(entity);

        AuthUser principal = new AuthUser(user.getId(), user.getEmail(), user.getRole());
        String accessToken = jwtService.generateAccessToken(principal);
        return TokenPairResponse.of(accessToken, rawToken, jwtService.accessTtlSeconds());
    }

    @Transactional
    public TokenPairResponse issueForNewSession(User user) {
        return issueTokenPair(user, UUID.randomUUID());
    }

    // noRollbackFor: the family revocation below must be committed even though we throw.
    @Transactional(noRollbackFor = ApiException.class)
    public TokenPairResponse refresh(String rawToken) {
        OffsetDateTime now = OffsetDateTime.now();
        RefreshToken stored = refreshTokens.findByTokenHash(TokenHasher.sha256Hex(rawToken))
                .orElseThrow(() -> new ApiException(ApiErrorCode.TOKEN_INVALID, "Unknown refresh token"));

        if (stored.isRevoked()) {
            revokeFamily(stored.getFamilyId(), now);
            throw new ApiException(ApiErrorCode.TOKEN_REUSED,
                    "Refresh token reuse detected; all sessions in this family were revoked");
        }
        if (stored.isExpired(now)) {
            throw new ApiException(ApiErrorCode.TOKEN_EXPIRED, "Refresh token expired");
        }
        User user = users.findById(stored.getUserId())
                .orElseThrow(() -> new ApiException(ApiErrorCode.TOKEN_INVALID, "Token owner not found"));
        if (!user.isActive()) {
            throw new ApiException(ApiErrorCode.USER_DISABLED, "Account is disabled");
        }

        stored.setRevokedAt(now);
        refreshTokens.save(stored);
        return issueTokenPair(user, stored.getFamilyId());
    }

    @Transactional
    public void revokeFamily(UUID familyId, OffsetDateTime now) {
        List<RefreshToken> live = refreshTokens.findByFamilyIdAndRevokedAtIsNull(familyId);
        for (RefreshToken token : live) {
            token.setRevokedAt(now);
        }
        refreshTokens.saveAll(live);
    }

    /** Logout revokes the whole family of the presented token (idempotent for unknown tokens). */
    @Transactional
    public void logout(String rawToken) {
        refreshTokens.findByTokenHash(TokenHasher.sha256Hex(rawToken)).ifPresent(stored ->
                revokeFamily(stored.getFamilyId(), OffsetDateTime.now()));
    }

    @Transactional
    public void revokeAllForUser(UUID userId) {
        refreshTokens.revokeAllForUser(userId, OffsetDateTime.now());
    }
}
