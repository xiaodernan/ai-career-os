package com.careeros.ai;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.util.HexFormat;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Epic 436 — a time-bound, caller-bound proof of *which service* called the AI
 * service. The shared {@code X-Internal-Token} answers "may this caller use the
 * internal door at all"; it says nothing about who the caller is, and it does not
 * expire, so a leaked token lets anyone on the internal network impersonate any
 * {@code X-User-Id} on any of the ~50 internal routes.
 *
 * This is the header-carried equivalent of a short-lived mTLS client identity.
 * A separate signing key proves the caller is the backend even if the shared token
 * leaks, and binding the proof to method, path and user stops a captured header
 * being replayed on another route or tenant. It is opt-in: a blank key sends no
 * headers and changes nothing about the existing deployment.
 *
 * The canonical string is deliberately tiny and shared verbatim with the Python
 * verifier ({@code ai-service/app/core/deps.py}) via a fixed cross-language test
 * vector — the one part of an HMAC handshake that can silently rot is the two
 * sides disagreeing about what they signed.
 */
public final class ServiceIdentitySigner {
    public static final String HEADER_ID = "X-Service-Id";
    public static final String HEADER_TIMESTAMP = "X-Service-Timestamp";
    public static final String HEADER_SIGNATURE = "X-Service-Signature";

    private static final String ALGORITHM = "HmacSHA256";

    private ServiceIdentitySigner() {
    }

    /** The exact bytes both sides sign. Never add a header that is not in here. */
    public static String canonical(String timestampMs, String method, String rawPath, String userId) {
        return timestampMs + "\n"
                + (method == null ? "" : method.toUpperCase(java.util.Locale.ROOT)) + "\n"
                + (rawPath == null ? "" : rawPath) + "\n"
                + (userId == null ? "" : userId);
    }

    /** Lower-case hex HMAC-SHA256 over {@link #canonical(String, String, String, String)}. */
    public static String sign(String key, String canonical) {
        try {
            Mac mac = Mac.getInstance(ALGORITHM);
            mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), ALGORITHM));
            return HexFormat.of().formatHex(mac.doFinal(canonical.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("could not sign the service identity", e);
        }
    }

    /**
     * Build the three headers for one outbound call, or {@code null} when the
     * feature is off. Supplying the clock keeps the helper testable without sleeping.
     */
    public static Headers forRequest(
            String key, String serviceId, String method, String rawPath, String userId, Clock clock) {
        if (key == null || key.isBlank()) return null;
        String timestamp = String.valueOf(Instant.now(clock).toEpochMilli());
        String canonical = canonical(timestamp, method, rawPath, userId);
        return new Headers(
                serviceId == null || serviceId.isBlank() ? "career-os-backend" : serviceId,
                timestamp,
                sign(key, canonical));
    }

    public record Headers(String id, String timestamp, String signature) {
    }

    /** Constant-time comparison for callers that also verify in Java. */
    public static boolean matches(String expected, String actual) {
        if (expected == null || actual == null) return false;
        return MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8),
                actual.getBytes(StandardCharsets.UTF_8));
    }
}
