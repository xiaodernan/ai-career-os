package com.careeros.common;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.http.server.ServletServerHttpResponse;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

class EnvelopeAdviceTest {

    private final EnvelopeAdvice advice = new EnvelopeAdvice();

    @Test
    void wrapsPayloadIntoSuccessEnvelope() {
        Object result = advice.beforeBodyWrite(Map.of("k", "v"), null, MediaType.APPLICATION_JSON,
                null, request("/api/v1/me"), response());
        @SuppressWarnings("unchecked")
        ApiResponse<Map<String, String>> envelope = (ApiResponse<Map<String, String>>) result;
        assertTrue(envelope.success());
        assertEquals("v", envelope.data().get("k"));
        assertEquals(null, envelope.error());
    }

    @Test
    void passesThroughAlreadyWrappedAndStreamingBodies() {
        ApiResponse<String> already = ApiResponse.ok("x");
        SseEmitter emitter = new SseEmitter();
        MockHttpServletRequest req = new MockHttpServletRequest("GET", "/api/v1/ai/stream/t1");
        assertSame(already, advice.beforeBodyWrite(already, null, MediaType.APPLICATION_JSON, null,
                new ServletServerHttpRequest(req), response()));
        assertSame(emitter, advice.beforeBodyWrite(emitter, null, MediaType.TEXT_EVENT_STREAM, null,
                new ServletServerHttpRequest(req), response()));
    }

    @Test
    void leavesOpenApiDocsUnwrapped() {
        Object spec = Map.of("openapi", "3.1.0");
        Object result = advice.beforeBodyWrite(spec, null, MediaType.APPLICATION_JSON, null,
                request("/api-docs"), response());
        assertSame(spec, result);
    }

    private static ServletServerHttpRequest request(String path) {
        return new ServletServerHttpRequest(new MockHttpServletRequest("GET", path));
    }

    private static ServletServerHttpResponse response() {
        return new ServletServerHttpResponse(new MockHttpServletResponse());
    }
}
