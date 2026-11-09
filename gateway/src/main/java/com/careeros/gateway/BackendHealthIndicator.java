package com.careeros.gateway;

import java.time.Duration;
import java.util.Map;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.ReactiveHealthIndicator;
import org.springframework.cloud.client.loadbalancer.reactive.ReactorLoadBalancerExchangeFilterFunction;
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
 *
 * <p>Epic 99.1: the probe resolves `backend` through the same load balancer the route
 * does, not through a second fixed address. A fixed address is a second answer to
 * "where is the backend": under the registry it is the laptop default, so the edge
 * would report itself down while forwarding traffic perfectly. One resolution path
 * means the health line describes the routing table the edge actually uses.
 */
@Component
public class BackendHealthIndicator implements ReactiveHealthIndicator {

    /** The service id the route and the probe share. */
    static final String SERVICE_ID = "backend";

    private final WebClient client;

    public BackendHealthIndicator(WebClient.Builder builder,
            ReactorLoadBalancerExchangeFilterFunction loadBalancer) {
        this.client = builder.filter(loadBalancer).build();
    }

    @Override
    public Mono<Health> health() {
        return client.get().uri("http://" + SERVICE_ID + "/api/v1/health")
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(Duration.ofSeconds(2))
                .map(body -> Health.up()
                        .withDetail("backendStatus", body.get("status"))
                        .build())
                .onErrorResume(error -> Mono.just(Health.down(error).build()));
    }
}
