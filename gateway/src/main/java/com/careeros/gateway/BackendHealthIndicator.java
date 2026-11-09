package com.careeros.gateway;

import java.time.Duration;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.ReactiveHealthIndicator;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

/**
 * The edge's own answer to "can I serve?" (Epic 88.2).
 *
 * <p>The backend has a health line already; this asks it, carrying the same two-second
 * bound the backend gives its own dependencies. Reaching the backend at all is the
 * question -- a backend that answers `degraded` is reachable, and its detail is copied
 * into this indicator's fields rather than turned into a red light here. That keeps one
 * place (the backend's line) deciding what its dependencies mean, while the edge reports
 * only the one thing it can know for itself.
 */
@Component
public class BackendHealthIndicator implements ReactiveHealthIndicator {

    private final WebClient client;

    public BackendHealthIndicator(WebClient.Builder builder,
            @Value("${GATEWAY_BACKEND_URI:http://localhost:8080}") String backend) {
        this.client = builder.baseUrl(backend).build();
    }

    @Override
    public Mono<Health> health() {
        return client.get().uri("/api/v1/health")
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(Duration.ofSeconds(2))
                .map(body -> Health.up()
                        .withDetail("backendStatus", body.get("status"))
                        .build())
                .onErrorResume(error -> Mono.just(Health.down(error).build()));
    }
}
