package com.careeros.auth.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.config.AppProperties;
import io.jsonwebtoken.Jwts;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;

/**
 * The access token's parse path, and the branches that keep a bad token out. A token
 * minted here is the only credential the API accepts, so every branch of
 * {@link JwtService#parseAccessToken} is a security branch: an expired token must be
 * refused as expired, a token someone else signed must be refused as invalid, and
 * a token whose *payload* was edited must be refused because the signature covers
 * the payload — the role-escalation path, where a "user" edits their own token into
 * an "admin" and replays it. Only the round trip and the rotation-reuse code touched
 * this class before; these are the branches that never had a test.
 */
class JwtServiceTest {

    private static final UUID USER_ID = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final String SECRET =
            "unit-test-secret-value-that-is-long-enough-for-hmac-requirements-0123456789";

    private static final AuthUser ALICE = new AuthUser(USER_ID, "ada@example.invalid", "user");

    private static AppProperties props(int ttlMinutes) {
        AppProperties props = new AppProperties();
        props.getJwt().setSecret(SECRET);
        props.getJwt().setAccessTtlMinutes(ttlMinutes);
        return props;
    }

    private JwtService jwt() {
        return new JwtService(props(15));
    }

    @Test
    void a_round_trip_returns_the_exact_principal_it_minted() {
        JwtService jwt = jwt();
        AuthUser parsed = jwt.parseAccessToken(jwt.generateAccessToken(ALICE));

        assertThat(parsed.id()).isEqualTo(USER_ID);
        assertThat(parsed.email()).isEqualTo("ada@example.invalid");
        assertThat(parsed.role()).isEqualTo("user");
        assertThat(parsed.familyId()).isNull();
        assertThat(jwt.accessTtlSeconds()).isEqualTo(15L * 60);
    }

    @Test
    void the_session_family_the_token_was_minted_for_survives_the_round_trip() {
        // 38.3: the session list marks the asking door; the access token is where the
        // backend learns which family that is, and a token without one marks nothing.
        UUID family = UUID.fromString("33333333-3333-4333-8333-333333333333");
        JwtService jwt = jwt();
        AuthUser parsed = jwt.parseAccessToken(
                jwt.generateAccessToken(new AuthUser(USER_ID, "ada@example.invalid", "user", family)));

        assertThat(parsed.familyId()).isEqualTo(family);
    }

    @Test
    void an_expired_token_is_refused_as_expired_not_as_invalid() {
        JwtService jwt = new JwtService(props(-1)); // minted with an expiry in the past

        ApiException ex = org.assertj.core.api.Assertions.catchThrowableOfType(
                () -> jwt.parseAccessToken(jwt.generateAccessToken(ALICE)),
                ApiException.class);

        assertThat(ex.code()).isEqualTo(ApiErrorCode.TOKEN_EXPIRED);
    }

    @Test
    void a_token_signed_with_another_secret_is_refused_as_invalid() {
        // The attacker's own token: valid JWT, valid claims, wrong key.
        AppProperties foreignProps = props(15);
        foreignProps.getJwt().setSecret("a-completely-different-secret-that-is-also-long-enough-2");
        String foreign = new JwtService(foreignProps)
                .generateAccessToken(new AuthUser(USER_ID, "attacker@example.invalid", "admin"));

        ApiException ex = org.assertj.core.api.Assertions.catchThrowableOfType(
                () -> jwt().parseAccessToken(foreign), ApiException.class);

        assertThat(ex.code()).isEqualTo(ApiErrorCode.TOKEN_INVALID);
    }

    @Test
    void an_edited_payload_is_refused_because_the_signature_covers_it() {
        // The role-escalation path: take a real "user" token, rewrite the role claim
        // in the payload, keep the signature. The signature still says the old bytes.
        String token = jwt().generateAccessToken(ALICE);
        String[] parts = token.split("\\.");
        String payload = new String(java.util.Base64.getUrlDecoder().decode(parts[1]),
                StandardCharsets.UTF_8)
                .replace("\"role\":\"user\"", "\"role\":\"admin\"");
        parts[1] = java.util.Base64.getUrlEncoder().withoutPadding()
                .encodeToString(payload.getBytes(StandardCharsets.UTF_8));
        String tampered = String.join(".", parts);

        assertThat(tampered).isNotEqualTo(token); // the payload really changed
        ApiException ex = org.assertj.core.api.Assertions.catchThrowableOfType(
                () -> jwt().parseAccessToken(tampered), ApiException.class);

        assertThat(ex.code()).isEqualTo(ApiErrorCode.TOKEN_INVALID);
    }

    @Test
    void a_non_access_token_type_is_refused() throws Exception {
        // Same key, valid signature, typ=refresh: a refresh token replayed as an access
        // token must not mint a session. JwtService's normalization is sha256(secret),
        // so the test can mint a refresh-shaped token against the same key.
        String refreshShaped = Jwts.builder()
                .subject(USER_ID.toString())
                .claim("email", ALICE.email())
                .claim("role", "user")
                .claim("typ", "refresh")
                .issuedAt(Date.from(Instant.now()))
                .expiration(Date.from(Instant.now().plusSeconds(3600)))
                .signWith(sameKey())
                .compact();

        ApiException ex = org.assertj.core.api.Assertions.catchThrowableOfType(
                () -> jwt().parseAccessToken(refreshShaped), ApiException.class);

        assertThat(ex.code()).isEqualTo(ApiErrorCode.TOKEN_MALFORMED);
    }

    @Test
    void a_token_with_no_type_claim_is_refused() throws Exception {
        String untyped = Jwts.builder()
                .subject(USER_ID.toString())
                .claim("email", ALICE.email())
                .issuedAt(Date.from(Instant.now()))
                .expiration(Date.from(Instant.now().plusSeconds(3600)))
                .signWith(sameKey())
                .compact();

        ApiException ex = org.assertj.core.api.Assertions.catchThrowableOfType(
                () -> jwt().parseAccessToken(untyped), ApiException.class);

        assertThat(ex.code()).isEqualTo(ApiErrorCode.TOKEN_MALFORMED);
    }

    @Test
    void a_token_whose_subject_is_not_a_uuid_is_refused() throws Exception {
        String badSubject = Jwts.builder()
                .subject("not-a-uuid")
                .claim("email", ALICE.email())
                .claim("typ", "access")
                .issuedAt(Date.from(Instant.now()))
                .expiration(Date.from(Instant.now().plusSeconds(3600)))
                .signWith(sameKey())
                .compact();

        ApiException ex = org.assertj.core.api.Assertions.catchThrowableOfType(
                () -> jwt().parseAccessToken(badSubject), ApiException.class);

        assertThat(ex.code()).isEqualTo(ApiErrorCode.TOKEN_MALFORMED);
    }

    @Test
    void a_string_that_is_not_a_jwt_at_all_is_refused_as_invalid() {
        for (String bad : new String[] {"", "   ", "not-a-jwt", "a.b", "a.b.c.d"}) {
            ApiException ex = org.assertj.core.api.Assertions.catchThrowableOfType(
                    () -> jwt().parseAccessToken(bad), ApiException.class);
            assertThat(ex.code()).isEqualTo(ApiErrorCode.TOKEN_INVALID);
        }
    }

    @Test
    void a_missing_secret_fails_at_startup_rather_than_at_first_use() {
        AppProperties props = new AppProperties();
        props.getJwt().setSecret("   ");
        assertThatThrownBy(() -> new JwtService(props))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.jwt.secret");
    }

    @Test
    void any_secret_length_is_normalized_into_a_valid_hmac_key() {
        // The constructor normalizes with sha256 so a short dev secret cannot produce
        // an invalid HMAC key — the round trip below is the proof.
        AppProperties props = new AppProperties();
        props.getJwt().setSecret("short");
        props.getJwt().setAccessTtlMinutes(15);
        JwtService jwt = new JwtService(props);

        assertThat(jwt.parseAccessToken(jwt.generateAccessToken(ALICE)).id()).isEqualTo(USER_ID);
    }

    private static SecretKey sameKey() throws Exception {
        return new SecretKeySpec(
                MessageDigest.getInstance("SHA-256").digest(SECRET.getBytes(StandardCharsets.UTF_8)),
                "HmacSHA256");
    }
}
