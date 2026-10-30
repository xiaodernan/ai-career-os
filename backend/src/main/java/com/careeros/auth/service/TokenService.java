package com.careeros.auth.service;

import com.careeros.auth.dto.SessionResponse;
import com.careeros.auth.dto.TokenPairResponse;
import com.careeros.auth.entity.RefreshToken;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.RefreshTokenRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.ClientInfo;
import com.careeros.config.AppProperties;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.BinaryOperator;
import java.util.stream.Collectors;
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
    public TokenPairResponse issueTokenPair(User user, UUID familyId, ClientInfo client) {
        String rawToken = TokenHasher.generateOpaqueToken();
        RefreshToken entity = new RefreshToken();
        entity.setUserId(user.getId());
        entity.setTokenHash(TokenHasher.sha256Hex(rawToken));
        entity.setFamilyId(familyId);
        entity.setUserAgent(client.userAgent());
        entity.setClientIp(client.clientIp());
        entity.setExpiresAt(OffsetDateTime.now().plus(refreshTtl));
        refreshTokens.save(entity);

        AuthUser principal = new AuthUser(user.getId(), user.getEmail(), user.getRole(), familyId);
        String accessToken = jwtService.generateAccessToken(principal);
        return TokenPairResponse.of(accessToken, rawToken, jwtService.accessTtlSeconds());
    }

    @Transactional
    public TokenPairResponse issueForNewSession(User user, ClientInfo client) {
        return issueTokenPair(user, UUID.randomUUID(), client);
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
                .orElseThrow(() -> new ApiException(ApiErrorCode.TOKEN_OWNER_NOT_FOUND, "Token owner not found"));
        if (!user.isActive()) {
            throw new ApiException(ApiErrorCode.USER_DISABLED, "Account is disabled");
        }

        stored.setRevokedAt(now);
        refreshTokens.save(stored);
        return issueTokenPair(user, stored.getFamilyId(),
                new ClientInfo(stored.getUserAgent(), stored.getClientIp()));
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

    /**
     * The account's open doors, newest activity first. One family is one session: rotation
     * replaces the token without adding a row the reader would read as a second device, so
     * the family's first token dates the session and its last token dates the last visit.
     * Revoked and expired tokens are left out — a session that can no longer refresh is
     * not something the reader can still close. {@code currentFamilyId} is the family the
     * asking access token was minted with; null (an old token) simply marks nothing.
     */
    @Transactional(readOnly = true)
    public List<SessionResponse> listSessions(UUID userId, UUID currentFamilyId) {
        Map<UUID, List<RefreshToken>> byFamily = refreshTokens
                .findByUserIdAndRevokedAtIsNullAndExpiresAtAfter(userId, OffsetDateTime.now())
                .stream()
                .collect(Collectors.groupingBy(RefreshToken::getFamilyId));
        if (byFamily.isEmpty()) {
            return List.of();
        }
        // The token that opened the family is retired by the first rotation, so the session's
        // start has to come from every row of the family, not from the live ones alone.
        Map<UUID, OffsetDateTime> started = refreshTokens.findByFamilyIdIn(byFamily.keySet()).stream()
                .collect(Collectors.toMap(RefreshToken::getFamilyId, RefreshToken::getCreatedAt,
                        BinaryOperator.minBy(Comparator.naturalOrder())));
        return byFamily.entrySet().stream()
                .map(entry -> new SessionResponse(
                        entry.getKey(),
                        entry.getValue().get(0).getUserAgent(),
                        entry.getValue().get(0).getClientIp(),
                        started.get(entry.getKey()),
                        entry.getValue().stream().map(RefreshToken::getCreatedAt)
                                .max(Comparator.naturalOrder()).orElse(null),
                        entry.getValue().stream().map(RefreshToken::getExpiresAt)
                                .max(Comparator.naturalOrder()).orElse(null),
                        entry.getKey().equals(currentFamilyId)))
                .sorted(Comparator.comparing(SessionResponse::lastSeenAt,
                        Comparator.nullsLast(Comparator.reverseOrder())))
                .toList();
    }

    /**
     * Revokes one of the caller's own sessions. A family id that is not live for this user —
     * whether it belongs to someone else or was already closed — is one 404, so the answer
     * never reveals which of the two it was. Closing the session that is asking is allowed:
     * it behaves like logout, with the access token dying at its short expiry.
     */
    @Transactional
    public void revokeSession(UUID userId, UUID familyId) {
        OffsetDateTime now = OffsetDateTime.now();
        List<RefreshToken> live = refreshTokens.findByFamilyIdAndRevokedAtIsNull(familyId).stream()
                .filter(token -> token.getUserId().equals(userId))
                .toList();
        if (live.isEmpty()) {
            throw new ApiException(ApiErrorCode.LOGIN_SESSION_NOT_FOUND, "Session not found");
        }
        for (RefreshToken token : live) {
            token.setRevokedAt(now);
        }
        refreshTokens.saveAll(live);
    }
}
