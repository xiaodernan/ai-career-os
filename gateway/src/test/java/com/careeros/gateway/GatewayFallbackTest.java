package com.careeros.gateway;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * Nothing behind the door still answers in the product's voice (Epic 88.2).
 *
 * <p>The configured upstream is a closed loopback port: connection refused is the one
 * failure a test can produce without a container, and it is also the failure a deploy
 * sees first when the backend's process is gone. The two assertions are the two callers
 * that matter: a browser gets the fallback sentence, and an orchestrator gets a health
 * line that names what it could not reach.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "GATEWAY_BACKEND_URI=http://127.0.0.1:1",
        "management.endpoint.health.show-details=always"
})
class GatewayFallbackTest {

    @Autowired
    private WebTestClient client;

    @Test
    void answersAsUnavailableInsteadOfForwardingAConnectionError() {
        client.get().uri("/api/v1/health")
                .exchange()
                .expectStatus().isEqualTo(503)
                .expectBody()
                .jsonPath("$.error").isEqualTo("backend-unavailable");
    }

    @Test
    void theHealthLineNamesTheBackendItCannotReach() {
        client.get().uri("/actuator/health")
                .exchange()
                .expectStatus().isEqualTo(503)
                .expectBody()
                .jsonPath("$.components.backend.status").isEqualTo("DOWN");
    }
}
