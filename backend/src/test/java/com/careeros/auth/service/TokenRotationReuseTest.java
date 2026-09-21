package com.careeros.auth.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.careeros.auth.dto.TokenPairResponse;
import com.careeros.auth.entity.RefreshToken;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.RefreshTokenRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.config.AppProperties;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** In-memory repository stubs (JDK proxies) exercise the rotation/reuse state machine without a DB. */
class TokenRotationReuseTest {

    private final List<RefreshToken> store = new ArrayList<>();
    private TokenService tokenService;
    private User user;

    @BeforeEach
    void setUp() {
        AppProperties props = new AppProperties();
        props.getJwt().setSecret("unit-test-secret-value-that-is-long-enough-for-hmac-requirements-0123456789");
        props.getJwt().setAccessTtlMinutes(15);
        props.getJwt().setRefreshTtlDays(30);

        user = new User();
        user.setId(UUID.randomUUID());
        user.setEmail("rotate@example.com");
        user.setDisplayName("Rotate");
        user.setRole("user");

        RefreshTokenRepository tokens = proxy(RefreshTokenRepository.class, (methodName, args) ->
                switch (methodName) {
                    case "findByTokenHash" -> store.stream()
                            .filter(t -> t.getTokenHash().equals(args[0])).findFirst();
                    case "save" -> {
                        RefreshToken entity = (RefreshToken) args[0];
                        if (!store.contains(entity)) {
                            store.add(entity);
                        }
                        yield entity;
                    }
                    case "findByFamilyIdAndRevokedAtIsNull" -> store.stream()
                            .filter(t -> t.getFamilyId().equals(args[0]) && t.getRevokedAt() == null).toList();
                    case "saveAll" -> args[0];
                    default -> throw newUnsupported(methodName);
                });
        UserRepository users = proxy(UserRepository.class, (methodName, args) ->
                switch (methodName) {
                    case "findById" -> user.getId().equals(args[0]) ? Optional.of(user) : Optional.empty();
                    default -> throw newUnsupported(methodName);
                });

        tokenService = new TokenService(tokens, users, new JwtService(props), props);
    }

    @Test
    void issuanceStoresHashedTokenAndReturnsOpaqueToken() {
        TokenPairResponse pair = tokenService.issueForNewSession(user);
        assertEquals(1, store.size());
        RefreshToken saved = store.get(0);
        assertEquals(TokenHasher.sha256Hex(pair.refreshToken()), saved.getTokenHash());
        assertNull(saved.getRevokedAt(), "fresh token must not be revoked");
        assertNotNull(saved.getFamilyId());
    }

    @Test
    void rotationRevokesPresentedTokenAndKeepsFamily() {
        TokenPairResponse first = tokenService.issueForNewSession(user);
        TokenPairResponse second = tokenService.refresh(first.refreshToken());

        assertNotEquals(first.refreshToken(), second.refreshToken(), "rotation must mint a new token");
        assertNotNull(store.stream().filter(t -> t.getTokenHash()
                .equals(TokenHasher.sha256Hex(first.refreshToken()))).findFirst().orElseThrow().getRevokedAt());
        UUID family = store.get(0).getFamilyId();
        assertTrue(store.stream().allMatch(t -> t.getFamilyId().equals(family)), "family must be preserved");
    }

    @Test
    void reusingRotatedTokenRevokesEntireFamily() {
        TokenPairResponse first = tokenService.issueForNewSession(user);
        TokenPairResponse second = tokenService.refresh(first.refreshToken());

        ApiException reuse = assertThrows(ApiException.class,
                () -> tokenService.refresh(first.refreshToken()));
        assertEquals(ApiErrorCode.TOKEN_REUSED, reuse.code());

        assertTrue(store.stream().allMatch(RefreshToken::isRevoked),
                "reuse detection must revoke every live token of the family");

        ApiException followUp = assertThrows(ApiException.class,
                () -> tokenService.refresh(second.refreshToken()));
        assertEquals(ApiErrorCode.TOKEN_REUSED, followUp.code(), "family successor must now be rejected too");
    }

    @Test
    void unknownTokenIsRejected() {
        ApiException ex = assertThrows(ApiException.class,
                () -> tokenService.refresh("no-such-token"));
        assertEquals(ApiErrorCode.TOKEN_INVALID, ex.code());
    }

    @Test
    void logoutRevokesFamilyAndBlocksFurtherRefresh() {
        TokenPairResponse pair = tokenService.issueForNewSession(user);
        tokenService.logout(pair.refreshToken());
        ApiException ex = assertThrows(ApiException.class, () -> tokenService.refresh(pair.refreshToken()));
        assertEquals(ApiErrorCode.TOKEN_REUSED, ex.code());
    }

    private static RuntimeException newUnsupported(String name) {
        return new UnsupportedOperationException(name + " not stubbed");
    }

    @SuppressWarnings("unchecked")
    private static <T> T proxy(Class<T> iface, Stub handler) {
        return (T) Proxy.newProxyInstance(iface.getClassLoader(), new Class<?>[] {iface},
                (p, method, args) -> {
                    if (method.getDeclaringClass() == Object.class) {
                        return switch (method.getName()) {
                            case "hashCode" -> System.identityHashCode(p);
                            case "equals" -> p == args[0];
                            default -> method.invoke(new Object());
                        };
                    }
                    return handler.invoke(method.getName(), args);
                });
    }

    @FunctionalInterface
    private interface Stub {
        Object invoke(String methodName, Object[] args) throws Throwable;
    }
}
