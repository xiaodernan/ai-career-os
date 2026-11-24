package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;

/**
 * Epic 436 — the Java half of a cross-language HMAC vector. The same canonical
 * string and expected hex are hard-coded in the Python gate
 * ({@code ai-service/tests/test_service_identity_proof.py}); either side drifting
 * turns one of the two red. No Spring context, no network, no model.
 */
class ServiceIdentitySignerTest {

    @Test
    void signsTheSharedCanonicalString() {
        String canonical = ServiceIdentitySigner.canonical(
                "1700000000000", "POST", "/internal/agents/chat", "u-1");
        assertThat(canonical).isEqualTo("1700000000000\nPOST\n/internal/agents/chat\nu-1");
        assertThat(ServiceIdentitySigner.sign("k", canonical))
                .isEqualTo("c39ab0411f4e844efd9e1f8422c4dc90a875f33828d80d042ae4d812033ec377");
    }

    @Test
    void uppercasesTheMethodAndToleratesANullUser() {
        assertThat(ServiceIdentitySigner.canonical("1", "get", "/internal/x", null))
                .isEqualTo("1\nGET\n/internal/x\n");
    }

    @Test
    void emitsNoHeadersWhenTheKeyIsBlank() {
        assertThat(ServiceIdentitySigner.forRequest(
                "", "career-os-backend", "GET", "/internal/x", "u-1", Clock.systemUTC()))
                .isNull();
        assertThat(ServiceIdentitySigner.forRequest(
                null, "career-os-backend", "GET", "/internal/x", "u-1", Clock.systemUTC()))
                .isNull();
    }

    @Test
    void stampsTheConfiguredIdAndASignatureOverTheActualRequest() {
        Clock fixed = Clock.fixed(Instant.ofEpochMilli(1_700_000_000_000L), ZoneOffset.UTC);
        ServiceIdentitySigner.Headers headers = ServiceIdentitySigner.forRequest(
                "k", "career-os-backend", "POST", "/internal/agents/chat", "u-1", fixed);
        assertThat(headers).isNotNull();
        assertThat(headers.id()).isEqualTo("career-os-backend");
        assertThat(headers.timestamp()).isEqualTo("1700000000000");
        assertThat(headers.signature())
                .isEqualTo("c39ab0411f4e844efd9e1f8422c4dc90a875f33828d80d042ae4d812033ec377");
    }

    @Test
    void comparesInConstantTime() {
        assertThat(ServiceIdentitySigner.matches("abc", "abc")).isTrue();
        assertThat(ServiceIdentitySigner.matches("abc", "abd")).isFalse();
        assertThat(ServiceIdentitySigner.matches(null, "abc")).isFalse();
    }
}
