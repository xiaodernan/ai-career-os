package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

/**
 * Whose address a request is counted against.
 *
 * X-Forwarded-For is written by whoever sends it, so it is only evidence when the deployment
 * declares a trusted proxy. These cases pin both modes, and the hop that is read when the
 * declaration is on: the last one, which is what the proxy itself wrote, never the first one,
 * where a client that pre-sent the header has already written its fiction.
 */
class ClientInfoTest {

    private static MockHttpServletRequest request(String remoteAddr, String forwardedFor) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRemoteAddr(remoteAddr);
        if (forwardedFor != null) {
            request.addHeader("X-Forwarded-For", forwardedFor);
        }
        return request;
    }

    @Test
    void withoutTheDeclarationTheSocketIsTheIdentity() {
        assertThat(ClientInfo.clientIp(request("192.0.2.5", "203.0.113.99"), false))
                .isEqualTo("192.0.2.5");
    }

    @Test
    void aDeclaredProxyIsBelieved() {
        assertThat(ClientInfo.clientIp(request("10.0.0.5", "203.0.113.7"), true))
                .isEqualTo("203.0.113.7");
    }

    @Test
    void theHopTheProxyWroteIsTheLastOneNotTheFirst() {
        // The proxy appended what it saw to a header the client had already written.
        assertThat(ClientInfo.clientIp(request("10.0.0.5", "192.0.2.77, 198.51.100.9"), true))
                .isEqualTo("198.51.100.9");
    }

    @Test
    void aDeclaredProxyWithNoHeaderFallsBackToTheSocket() {
        assertThat(ClientInfo.clientIp(request("192.0.2.5", null), true)).isEqualTo("192.0.2.5");
        assertThat(ClientInfo.clientIp(request("192.0.2.5", "   "), true)).isEqualTo("192.0.2.5");
        assertThat(ClientInfo.clientIp(request("192.0.2.5", " , , "), true)).isEqualTo("192.0.2.5");
    }

    @Test
    void theSessionRecordCarriesTheAgentAndTheAddressWithinTheColumnWidths() {
        MockHttpServletRequest request = request("192.0.2.5", "203.0.113.7");
        request.addHeader("User-Agent", "A".repeat(300));
        ClientInfo info = ClientInfo.from(request, true);
        assertThat(info.userAgent()).hasSize(255);
        assertThat(info.clientIp()).isEqualTo("203.0.113.7");

        MockHttpServletRequest longAddress = request("1".repeat(60), null);
        assertThat(ClientInfo.from(longAddress, false).clientIp()).hasSize(45);
    }

    @Test
    void theRecordRefusesTheHeaderWhenNoProxyIsDeclared() {
        MockHttpServletRequest request = request("192.0.2.5", "203.0.113.7");
        request.addHeader("User-Agent", "JUnit");
        ClientInfo info = ClientInfo.from(request, false);
        assertThat(info.clientIp()).isEqualTo("192.0.2.5");
        assertThat(info.userAgent()).isEqualTo("JUnit");
    }
}
