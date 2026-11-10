package com.careeros.configserver;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;

/**
 * The config server's optional shared-secret gate (Epic 114).
 *
 * <p>With {@code CONFIG_SERVER_TOKEN} set, only requests carrying the matching
 * {@code X-Config-Token} header reach the config surface; the health probe stays
 * anonymous. Unset keeps the dev posture.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {
                "spring.profiles.active=native",
                "spring.cloud.config.server.native.search-locations=classpath:/config-repo",
                "CONFIG_SERVER_TOKEN=op-secret-operations-token"
        })
class ConfigServerTokenGateTest {

    @LocalServerPort
    int port;

    @Autowired
    TestRestTemplate rest;

    private HttpHeaders withToken(String token) {
        HttpHeaders headers = new HttpHeaders();
        if (token != null) {
            headers.set(ConfigTokenFilter.HEADER, token);
        }
        return headers;
    }

    @Test
    void refusesConfigRequestWithoutToken() {
        ResponseEntity<String> response = rest.exchange(
                "http://localhost:" + port + "/career-os-backend/default",
                org.springframework.http.HttpMethod.GET,
                new HttpEntity<>(withToken(null)), String.class);
        assertThat(response.getStatusCode().is4xxClientError()).isTrue();
        assertThat(response.getBody()).contains("config-token-required");
    }

    @Test
    void admitsConfigRequestWithToken() {
        ResponseEntity<String> response = rest.exchange(
                "http://localhost:" + port + "/career-os-backend/default",
                org.springframework.http.HttpMethod.GET,
                new HttpEntity<>(withToken("op-secret-operations-token")), String.class);
        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).contains("careeros.config-server.service");
    }

    @Test
    void refusesWrongToken() {
        ResponseEntity<String> response = rest.exchange(
                "http://localhost:" + port + "/career-os-backend/default",
                org.springframework.http.HttpMethod.GET,
                new HttpEntity<>(withToken("nope")), String.class);
        assertThat(response.getStatusCode().is4xxClientError()).isTrue();
    }

    @Test
    void healthStaysOpenForTheContainerProbe() {
        ResponseEntity<String> response = rest.getForEntity(
                "http://localhost:" + port + "/actuator/health", String.class);
        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
    }
}