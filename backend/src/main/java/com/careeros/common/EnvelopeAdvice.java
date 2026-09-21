package com.careeros.common;

import org.springframework.core.MethodParameter;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyAdvice;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * Wraps every controller return value in the unified envelope. Exceptions are rendered by
 * GlobalExceptionHandler which already returns ApiResponse, and SSE/streaming/resource bodies
 * must pass through untouched.
 */
@RestControllerAdvice
public class EnvelopeAdvice implements ResponseBodyAdvice<Object> {

    @Override
    public boolean supports(MethodParameter returnType, Class converterType) {
        return true;
    }

    @Override
    public Object beforeBodyWrite(Object body, MethodParameter returnType, MediaType contentType,
                                  Class converterType, ServerHttpRequest request, ServerHttpResponse response) {
        if (body instanceof ApiResponse<?> || body instanceof SseEmitter || body instanceof Resource
                || body instanceof byte[]) {
            return body;
        }
        String path = request.getURI().getPath();
        if (path.startsWith("/api-docs") || path.startsWith("/v3/api-docs") || path.startsWith("/swagger-ui")) {
            return body;
        }
        return ApiResponse.ok(body);
    }
}
