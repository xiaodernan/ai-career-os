package com.careeros.auth.security;

import com.careeros.common.ApiError;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiResponse;
import com.careeros.config.AppProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.http.MediaType;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Guards /api/internal/** (service-to-service surface consumed by ai-service).
 * Requires X-Internal-Token == app.internal.token, compared in constant time.
 */
public class InternalApiFilter extends OncePerRequestFilter {

    private final AppProperties props;
    private final ObjectMapper objectMapper;

    public InternalApiFilter(AppProperties props, ObjectMapper objectMapper) {
        this.props = props;
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith("/api/internal");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String presented = request.getHeader("X-Internal-Token");
        String expected = props.getInternal().getToken();
        boolean ok = presented != null && expected != null
                && MessageDigest.isEqual(presented.getBytes(StandardCharsets.UTF_8),
                        expected.getBytes(StandardCharsets.UTF_8));
        if (!ok) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            objectMapper.writeValue(response.getOutputStream(),
                    ApiResponse.error(ApiError.of(ApiErrorCode.UNAUTHORIZED, "Invalid internal token")));
            return;
        }
        chain.doFilter(request, response);
    }
}
