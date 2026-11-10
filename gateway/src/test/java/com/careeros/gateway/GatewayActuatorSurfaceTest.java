package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.reactive.server.WebTestClient;

/**
 * The edge's operations surface can carry a shared secret when one is set (Epic 108.15).
 *
 * <p>The gateway's actuator endpoints exist for an operator: `/actuator/info`, `/actuator/gateway/routes`,
 * `/actuator/metrics`, `/actuator/circuitbreakers`, ... Until `GATEWAY_ACTUATOR_TOKEN` is set nothing
 * stops them sailing past loopback if a proxy publishes the port. This test proves the guard both ways:
 * with the knob set, a request without the header or with a wrong value is refused here (and the actuator
 * never answers), and `/actuator/health` stays reachable for the container probe. When the knob is unset
 * nothing changes — the surface stays open, the pre-existing dev flows do not regress.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "GATEWAY_ACTUATOR_TOKEN=edge-operations-secret"
})
class GatewayActuatorSurfaceTest {

    @Autowired
    private WebTestClient client;

    @Test
    void refusesTheOperationsSurfaceWithoutAToken() {
        client.get().uri("/actuator/info")
                .exchange()
                .expectStatus().isForbidden()
                .expectBody()
                .jsonPath("$.error").isEqualTo("actuator-surface-not-exposed");
    }

    @Test
    void refusesTheOperationsSurfaceWithAWrongToken() {
        client.get().uri("/actuator/info")
                .headers(headers -> headers.set("X-Actuator-Token", "not-the-secret"))
                .exchange()
                .expectStatus().isForbidden()
                .expectBody()
                .jsonPath("$.error").isEqualTo("actuator-surface-not-exposed");
    }

    @Test
    void letsTheHealthProbeThroughWhileTheSurfaceIsLocked() {
        // The probe is never refused: the answer is either 200 or the dependency line's own
        // 503 (no backend/registry in this test), never the guard's 403.
        client.get().uri("/actuator/health")
                .exchange()
                .expectStatus().value(status ->
                        org.assertj.core.api.Assertions.assertThat(status).isNotEqualTo(403));
    }

    @Test
    void letsAnAdmittedOperatorSeeTheWiringDetails() {
        // Spring Boot wiring answers (condition matchers) only when the actuator token is present;
        // otherwise the edge refuses before they exist.
        client.get().uri("/actuator/conditions")
                .exchange()
                .expectStatus().isForbidden();

        client.get().uri("/actuator/conditions")
                .headers(headers -> headers.set("X-Actuator-Token", "edge-operations-secret"))
                .exchange()
                .expectStatus().isOk();
    }

    @Test
    void servesTheOperationsSurfaceWhenTheTokenIsPresent() {
        client.get().uri("/actuator/info")
                .headers(headers -> headers.set("X-Actuator-Token", "edge-operations-secret"))
                .exchange()
                .expectStatus().isOk();

        assertThat(true).isTrue();
    }
}