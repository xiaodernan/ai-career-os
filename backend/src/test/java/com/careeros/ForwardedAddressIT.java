package com.careeros;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/**
 * The login bucket of a service reached directly.
 *
 * `docs/SECURITY.md` measured the bypass: with the limiter reading X-Forwarded-For
 * unconditionally, six logins carrying six different header values all returned 401 and
 * Redis held six buckets. This class speaks as a direct client -- the trust declaration is
 * off, which is the shipped default -- and sets the socket address itself, because MockMvc
 * has no socket to speak from. Two logins from one address fill its bucket whatever the
 * header says; the third is refused, and rotating the header bought nothing. A different
 * socket address still has its own window, so the refusal is the shared identity, not a
 * limiter that stopped working.
 *
 * <p>The trusted topology is what every other IT exercises through
 * {@link AbstractIntegrationTest}'s declaration and one-header-per-client requests.
 */
@TestPropertySource(properties = {
        "app.http.trust-forwarded-for=false",
        "app.ratelimit.auth-per-minute=2"
})
class ForwardedAddressIT extends AbstractIntegrationTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    @Test
    void aDirectClientCannotBuyFreshBucketsByRotatingTheHeader() throws Exception {
        String body = JSON.writeValueAsString(Map.of(
                "email", "spoof-" + UUID.randomUUID() + "@example.com",
                "password", "WrongPassw0rd!!"));

        for (int i = 1; i <= 2; i++) {
            mvc.perform(post("/api/v1/auth/login")
                            .with(socket("192.0.2.9"))
                            .header("X-Forwarded-For", "203.0.113." + i)
                            .contentType(MediaType.APPLICATION_JSON).content(body))
                    .andExpect(status().isUnauthorized());
        }
        mvc.perform(post("/api/v1/auth/login")
                        .with(socket("192.0.2.9"))
                        .header("X-Forwarded-For", "203.0.113.3")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isTooManyRequests())
                .andExpect(jsonPath("$.error.code").value("RATE_LIMITED"));

        mvc.perform(post("/api/v1/auth/login")
                        .with(socket("192.0.2.10"))
                        .header("X-Forwarded-For", "203.0.113.3")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isUnauthorized());
    }

    private static RequestPostProcessor socket(String address) {
        return request -> {
            request.setRemoteAddr(address);
            return request;
        };
    }
}
