package com.careeros.config;

import com.careeros.auth.security.InternalApiFilter;
import com.careeros.auth.security.JwtAuthFilter;
import com.careeros.auth.service.JwtService;
import com.careeros.common.ApiError;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiResponse;
import com.careeros.ratelimit.RateLimitFilter;
import com.careeros.ratelimit.RedisSlidingWindowRateLimiter;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.DispatcherType;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http, AppProperties props, JwtService jwtService,
                                                   RedisSlidingWindowRateLimiter rateLimiter,
                                                   ObjectMapper objectMapper) throws Exception {
        JwtAuthFilter jwtAuthFilter = new JwtAuthFilter(jwtService);
        InternalApiFilter internalApiFilter = new InternalApiFilter(props, objectMapper);
        RateLimitFilter rateLimitFilter = new RateLimitFilter(props, rateLimiter, objectMapper);

        http
                // CSRF disabled: the API is authenticated exclusively with bearer tokens sent in
                // the Authorization header (no cookie-based credentials), so a cross-site request
                // cannot carry this user's credentials and there is no CSRF attack surface.
                .csrf(csrf -> csrf.disable())
                .cors(cors -> cors.configurationSource(corsConfigurationSource(props)))
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // An async dispatch is the continuation of a request that was already
                        // authorized: the filter chain runs again when the emitter is written to,
                        // and with a stateless session the security context is gone by then, so
                        // `anyRequest().authenticated()` denies it. That killed the copilot's
                        // streaming turn in the browser -- the client fell back to the blocking
                        // pair, so the screen looked right and nothing was ever streamed.
                        .dispatcherTypeMatchers(DispatcherType.ASYNC, DispatcherType.ERROR).permitAll()
                        .requestMatchers("/api/v1/auth/**").permitAll()
                        // The mail-settings page and its one-click POST (roadmap 23.1): a mail
                        // client cannot carry a bearer token, so the account id plus an HMAC in
                        // the path is the credential. This prefix serves nothing else; a route
                        // added under it is public until it is moved.
                        .requestMatchers("/api/v1/mail/**").permitAll()
                        .requestMatchers("/api-docs/**", "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                        .requestMatchers("/api/v1/health").permitAll()
                        // Observability surface, pinned to the two exposed endpoints rather
                        // than /actuator/**: the scrape is read-only Micrometer metrics and
                        // health is a liveness probe. Production can restrict
                        // /actuator/prometheus at the reverse proxy (docs/SECURITY.md).
                        .requestMatchers("/actuator/health", "/actuator/prometheus").permitAll()
                        // Service-to-service surface: authenticated by the shared internal token,
                        // not by a user JWT (see InternalApiFilter).
                        .requestMatchers("/api/internal/**").permitAll()
                        .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                        .anyRequest().authenticated())
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((request, response, e) ->
                                writeEnvelope(response, 401,
                                        ApiError.of(ApiErrorCode.UNAUTHORIZED, "Authentication required")))
                        .accessDeniedHandler((request, response, e) ->
                                writeEnvelope(response, 403,
                                        ApiError.of(ApiErrorCode.FORBIDDEN, "Access denied"))))
                .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
                .addFilterBefore(internalApiFilter, JwtAuthFilter.class)
                // Rate limiting runs after JWT so AI-endpoint limits can key off the user id.
                .addFilterAfter(rateLimitFilter, JwtAuthFilter.class);
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource(AppProperties props) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(props.getCors().getAllowedOrigins());
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type", "X-Internal-Token"));
        config.setMaxAge(3600L);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(BCryptPasswordEncoder.BCryptVersion.$2B, 12);
    }

    private static void writeEnvelope(jakarta.servlet.http.HttpServletResponse response,
                                      int status, ApiError error) throws java.io.IOException {
        response.setStatus(status);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write(com.careeros.common.EnvelopeJson.MAPPER
                .writeValueAsString(ApiResponse.error(error)));
    }
}
