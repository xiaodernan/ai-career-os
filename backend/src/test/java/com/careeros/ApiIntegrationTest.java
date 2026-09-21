package com.careeros;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import com.careeros.support.FakeAiServiceClientConfig.FakeAiServiceClient;
import com.careeros.support.InMemoryStorageConfig.InMemoryStorageService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.AfterEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

/**
 * Base for domain API integration tests: reuses the localhost infra from
 * {@link AbstractIntegrationTest}, wires the fake ai-service double and in-memory storage, and
 * exposes tiny register/auth helpers so each test can focus on its module's contract.
 */
public abstract class ApiIntegrationTest extends AbstractIntegrationTest {

    protected static final ObjectMapper MAPPER = new ObjectMapper();
    private static final AtomicLong IP_SEQ = new AtomicLong(500);

    @Autowired
    protected FakeAiServiceClient ai;

    @Autowired
    protected InMemoryStorageService storage;

    @AfterEach
    void resetAiDouble() {
        ai.reset();
    }

    protected static String freshIp() {
        long n = IP_SEQ.incrementAndGet();
        return "10.88." + (n % 250) + "." + (n / 250 % 250);
    }

    /** Registers a fresh user and returns its bearer access token. */
    protected String register(String email) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/register")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"Str0ngPassphrase!23\","
                                + "\"displayName\":\"Domain Tester\"}"))
                .andReturn();
        JsonNode data = MAPPER.readTree(result.getResponse().getContentAsString()).path("data");
        return data.path("tokens").path("accessToken").asText();
    }

    protected static String json(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}

