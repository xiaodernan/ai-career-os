package com.careeros.configserver;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * Optional opaque-token gate for the config surface (Epic 114).
 *
 * <p>Set {@code CONFIG_SERVER_TOKEN} and every request to the config server must carry the
 * matching {@code X-Config-Token} header; unset keeps the dev/loopback behavior where the
 * native examples assume nothing secret is served. The actuator probe stays anonymous so a
 * container healthcheck never blocks on a rotation.
 *
 * <p>The token is a shared bearer, not a full auth system — it is exactly what a single-node
 * native repo wants: no external dependencies, one env var, rotation by env-step alone.
 */
public class ConfigTokenFilter extends HttpFilter {

    public static final String HEADER = "X-Config-Token";
    public static final String ENV = "CONFIG_SERVER_TOKEN";

    private final String token;

    public ConfigTokenFilter(String token) {
        this.token = token == null ? "" : token.trim();
    }

    @Override
    protected void doFilter(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        String path = request.getRequestURI();
        if (token.isBlank()
                || path.startsWith("/actuator/health")) {
            chain.doFilter(request, response);
            return;
        }
        String presented = request.getHeader(HEADER);
        if (token.equals(presented)) {
            chain.doFilter(request, response);
            return;
        }
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json");
        response.getWriter().write("{\"error\":\"config-token-required\"}");
    }
}