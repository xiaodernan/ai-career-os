package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;

import jakarta.servlet.FilterChain;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class RequestIdFilterTest {

    private static final String UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    private final RequestIdFilter filter = new RequestIdFilter();

    @AfterEach
    void clearMdc() {
        MDC.clear();
    }

    @Test
    void mintsAnIdWhenNoneArrivesAndTheChainSeesItAlready() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/me");
        MockHttpServletResponse response = new MockHttpServletResponse();
        AtomicReference<String> headerDuringChain = new AtomicReference<>();
        AtomicReference<String> mdcDuringChain = new AtomicReference<>();
        FilterChain chain = (req, res) -> {
            headerDuringChain.set(((MockHttpServletResponse) res).getHeader(RequestIdFilter.HEADER));
            mdcDuringChain.set(MDC.get(RequestIdFilter.MDC_KEY));
        };

        filter.doFilter(request, response, chain);

        String id = response.getHeader(RequestIdFilter.HEADER);
        assertThat(id).matches(UUID);
        // Set before the chain, so an error handler and the access log agree on one id.
        assertThat(headerDuringChain.get()).isEqualTo(id);
        assertThat(mdcDuringChain.get()).isEqualTo(id);
        // The pooled thread does not carry the request's id into the next one.
        assertThat(MDC.get(RequestIdFilter.MDC_KEY)).isNull();
    }

    @Test
    void echoesAWellFormedIdFromAProxy() throws Exception {
        for (String inbound : new String[] {"edge-7c1d4f9a", "0123456789abcdef0123456789abcdef",
                "A.b-c_d.1234", "0".repeat(64)}) {
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/me");
            request.addHeader(RequestIdFilter.HEADER, inbound);
            MockHttpServletResponse response = new MockHttpServletResponse();

            filter.doFilter(request, response, (req, res) -> { });

            assertThat(response.getHeader(RequestIdFilter.HEADER))
                    .as("the proxy's id %s is kept", inbound)
                    .isEqualTo(inbound);
        }
    }

    @Test
    void replacesAnIdTheLogCannotCarry() throws Exception {
        for (String inbound : new String[] {"", "short", "has space", "line\nbreak", "tab\there",
                "-starts-with-a-dash", "0".repeat(65), "id%0d%0ainjected"}) {
            MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/me");
            request.addHeader(RequestIdFilter.HEADER, inbound);
            MockHttpServletResponse response = new MockHttpServletResponse();

            filter.doFilter(request, response, (req, res) -> { });

            assertThat(response.getHeader(RequestIdFilter.HEADER))
                    .as("the malformed id %s is replaced, not echoed", inbound)
                    .matches(UUID)
                    .isNotEqualTo(inbound);
        }
    }
}
