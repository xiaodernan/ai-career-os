package com.careeros.auth.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.stereotype.Service;
import com.careeros.config.AppProperties;

/** HS256 access-token issuing/parsing. */
@Service
public class JwtService {

    private final SecretKey key;
    private final Duration accessTtl;

    public JwtService(AppProperties props) {
        String secret = props.getJwt().getSecret();
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException("app.jwt.secret must be configured");
        }
        // Normalize any secret to 256 bits so HMAC key strength is always valid.
        this.key = new SecretKeySpec(sha256(secret), "HmacSHA256");
        this.accessTtl = Duration.ofMinutes(props.getJwt().getAccessTtlMinutes());
    }

    public long accessTtlSeconds() {
        return accessTtl.toSeconds();
    }

    public String generateAccessToken(AuthUser user) {
        Instant now = Instant.now();
        var builder = Jwts.builder()
                .subject(user.id().toString())
                .claim("email", user.email())
                .claim("role", user.role())
                .claim("typ", "access")
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plus(accessTtl)));
        // The session list marks the door that is asking; the access token is what makes
        // that possible without the browser having to remember a family id (38.3).
        if (user.familyId() != null) {
            builder.claim("fid", user.familyId().toString());
        }
        return builder.signWith(key).compact();
    }

    /** @throws ApiException TOKEN_EXPIRED / TOKEN_INVALID when the token is not usable. */
    public AuthUser parseAccessToken(String token) {
        Claims claims;
        try {
            claims = Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
        } catch (ExpiredJwtException e) {
            throw new ApiException(ApiErrorCode.TOKEN_EXPIRED, "Access token expired");
        } catch (JwtException | IllegalArgumentException e) {
            throw new ApiException(ApiErrorCode.TOKEN_INVALID, "Invalid access token");
        }
        if (!"access".equals(claims.get("typ", String.class))) {
            throw new ApiException(ApiErrorCode.TOKEN_MALFORMED, "Not an access token");
        }
        try {
            String fid = claims.get("fid", String.class);
            return new AuthUser(UUID.fromString(claims.getSubject()),
                    claims.get("email", String.class), claims.get("role", String.class),
                    fid == null ? null : UUID.fromString(fid));
        } catch (IllegalArgumentException e) {
            throw new ApiException(ApiErrorCode.TOKEN_MALFORMED, "Malformed token subject");
        }
    }

    private static byte[] sha256(String value) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}
