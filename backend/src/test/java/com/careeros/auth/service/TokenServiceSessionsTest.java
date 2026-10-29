package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.careeros.auth.dto.SessionResponse;
import com.careeros.auth.dto.TokenPairResponse;
import com.careeros.auth.entity.RefreshToken;
import com.careeros.auth.entity.User;
import com.careeros.auth.repository.RefreshTokenRepository;
import com.careeros.auth.repository.UserRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.ClientInfo;
import com.careeros.config.AppProperties;
import java.lang.reflect.Field;
import java.lang.reflect.Proxy;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The session model behind roadmap 25: a refresh-token family is one signed-in device,
 * named by the user-agent and address that opened it. These tests pin the naming, the
 * folding of rotations back into their family, and the rule that one account can only
 * close its own live sessions.
 */
class TokenServiceSessionsTest {

    private static final OffsetDateTime T0 = OffsetDateTime.parse("2026-10-01T09:00:00Z");

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
        user.setEmail("sessions@example.com");
        user.setDisplayName("Sessions");
        user.setRole("user");

        RefreshTokenRepository tokens = proxy(RefreshTokenRepository.class, (methodName, args) ->
                switch (methodName) {
                    case "save" -> {
                        RefreshToken entity = (RefreshToken) args[0];
                        if (!store.contains(entity)) {
                            store.add(entity);
                        }
                        yield entity;
                    }
                    case "saveAll" -> {
                        for (RefreshToken entity : (List<RefreshToken>) args[0]) {
                            if (!store.contains(entity)) {
                                store.add(entity);
                            }
                        }
                        yield args[0];
                    }
                    case "findByTokenHash" -> store.stream()
                            .filter(t -> t.getTokenHash().equals(args[0])).findFirst();
                    case "findByFamilyIdAndRevokedAtIsNull" -> store.stream()
                            .filter(t -> t.getFamilyId().equals(args[0]) && t.getRevokedAt() == null).toList();
                    case "findByFamilyIdIn" -> store.stream()
                            .filter(t -> ((java.util.Collection<UUID>) args[0]).contains(t.getFamilyId()))
                            .toList();
                    case "findByUserIdAndRevokedAtIsNullAndExpiresAtAfter" -> store.stream()
                            .filter(t -> t.getUserId().equals(args[0]) && t.getRevokedAt() == null
                                    && t.getExpiresAt().isAfter((OffsetDateTime) args[1]))
                            .toList();
                    default -> throw new UnsupportedOperationException(methodName + " not stubbed");
                });
        UserRepository users = proxy(UserRepository.class, (methodName, args) ->
                switch (methodName) {
                    case "findById" -> user.getId().equals(args[0]) ? Optional.of(user) : Optional.empty();
                    default -> throw new UnsupportedOperationException(methodName + " not stubbed");
                });

        tokenService = new TokenService(tokens, users, new JwtService(props), props);
    }

    @Test
    void issuanceRecordsWhoOpenedTheSession() {
        tokenService.issueForNewSession(user, new ClientInfo("Mozilla/5.0 (Macintosh) Safari/605", "203.0.113.9"));

        assertThat(store).hasSize(1);
        assertThat(store.get(0).getUserAgent()).isEqualTo("Mozilla/5.0 (Macintosh) Safari/605");
        assertThat(store.get(0).getClientIp()).isEqualTo("203.0.113.9");
    }

    @Test
    void rotationStaysInTheFamilyAndKeepsItsName() {
        TokenPairResponse first = tokenService.issueForNewSession(user, new ClientInfo("JUnit/5", "198.51.100.4"));
        TokenPairResponse second = tokenService.refresh(first.refreshToken());

        assertThat(store).hasSize(2);
        RefreshToken rotated = store.get(1);
        assertThat(rotated.getFamilyId()).isEqualTo(store.get(0).getFamilyId());
        assertThat(rotated.getUserAgent()).isEqualTo("JUnit/5");
        assertThat(rotated.getClientIp()).isEqualTo("198.51.100.4");
        assertThat(second.refreshToken()).isNotEqualTo(first.refreshToken());
    }

    @Test
    void listingFoldsRotationIntoOneSessionAndOrdersByLastVisit() {
        TokenPairResponse laptop = tokenService.issueForNewSession(user, new ClientInfo("Laptop", "203.0.113.1"));
        stamp(store.get(0), T0);

        tokenService.issueForNewSession(user, new ClientInfo("Phone", "198.51.100.2"));
        stamp(store.get(1), T0.plusMinutes(5));

        tokenService.refresh(laptop.refreshToken());
        stamp(store.get(2), T0.plusMinutes(30));

        List<SessionResponse> sessions = tokenService.listSessions(user.getId());

        assertThat(sessions).hasSize(2);
        SessionResponse newest = sessions.get(0);
        assertThat(newest.userAgent()).isEqualTo("Laptop");
        assertThat(newest.startedAt()).isEqualTo(T0);
        assertThat(newest.lastSeenAt()).isEqualTo(T0.plusMinutes(30));
        assertThat(sessions.get(1).userAgent()).isEqualTo("Phone");
    }

    @Test
    void listingLeavesOutClosedAndExpiredSessions() {
        tokenService.issueForNewSession(user, new ClientInfo("Live", "203.0.113.1"));
        stamp(store.get(0), T0);

        tokenService.issueForNewSession(user, new ClientInfo("Closed", "203.0.113.2"));
        stamp(store.get(1), T0.plusMinutes(1));
        tokenService.revokeSession(user.getId(), store.get(1).getFamilyId());

        tokenService.issueForNewSession(user, new ClientInfo("Expired", "203.0.113.3"));
        stamp(store.get(2), T0.plusMinutes(2));
        store.get(2).setExpiresAt(T0.plusMinutes(3));

        List<SessionResponse> sessions = tokenService.listSessions(user.getId());

        assertThat(sessions).singleElement().satisfies(session ->
                assertThat(session.userAgent()).isEqualTo("Live"));
    }

    @Test
    void closingOneSessionTouchesOnlyThatFamily() {
        tokenService.issueForNewSession(user, new ClientInfo("Keep", "203.0.113.1"));
        UUID keep = store.get(0).getFamilyId();
        tokenService.issueForNewSession(user, new ClientInfo("Close", "203.0.113.2"));
        UUID close = store.get(1).getFamilyId();

        tokenService.revokeSession(user.getId(), close);

        assertThat(store.stream().filter(t -> t.getFamilyId().equals(keep)))
                .allMatch(t -> t.getRevokedAt() == null);
        assertThat(store.stream().filter(t -> t.getFamilyId().equals(close)))
                .allMatch(RefreshToken::isRevoked);
    }

    @Test
    void closingAFamilyThatIsNotTheCallersIsOneNotFoundAndTouchesNothing() {
        tokenService.issueForNewSession(user, new ClientInfo("Mine", "203.0.113.1"));

        RefreshToken stranger = new RefreshToken();
        stranger.setUserId(UUID.randomUUID());
        stranger.setTokenHash("stranger-hash");
        stranger.setFamilyId(UUID.randomUUID());
        stranger.setExpiresAt(OffsetDateTime.now().plusDays(1));
        store.add(stranger);

        ApiException ex = assertThrows(ApiException.class,
                () -> tokenService.revokeSession(user.getId(), stranger.getFamilyId()));

        assertEquals(ApiErrorCode.LOGIN_SESSION_NOT_FOUND, ex.code());
        assertThat(store).allMatch(t -> t.getRevokedAt() == null);
    }

    @Test
    void closingAnAlreadyClosedFamilyAnswersTheSameNotFound() {
        tokenService.issueForNewSession(user, new ClientInfo("Phone", "203.0.113.1"));
        UUID family = store.get(0).getFamilyId();

        tokenService.revokeSession(user.getId(), family);

        ApiException ex = assertThrows(ApiException.class,
                () -> tokenService.revokeSession(user.getId(), family));
        assertEquals(ApiErrorCode.LOGIN_SESSION_NOT_FOUND, ex.code());
    }

    /** created_at is filled by Hibernate on insert; the proxy store bypasses it, so tests stamp it. */
    private static void stamp(RefreshToken token, OffsetDateTime at) {
        try {
            Field field = RefreshToken.class.getDeclaredField("createdAt");
            field.setAccessible(true);
            field.set(token, at);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
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
