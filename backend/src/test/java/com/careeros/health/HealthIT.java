package com.careeros.health;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.AbstractIntegrationTest;
import com.careeros.support.FakeAiServiceClientConfig.FakeAiServiceClient;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * The health line against the real database and Redis (39.1).
 *
 * <p>The unit test pins the arithmetic over mocks; this one states the deployment's promise:
 * with every half answering the line says {@code ok}, and with the AI half gone it still
 * answers <b>200</b> and says which half is missing. The object store here is the in-memory
 * test bean, which answers by construction -- the MinIO probe is the same bucket-existence
 * call boot already makes, exercised by every deployment rather than this suite.
 */
class HealthIT extends AbstractIntegrationTest {

    @Autowired
    private FakeAiServiceClient ai;

    @AfterEach
    void resetAi() {
        ai.reset();
    }

    @Test
    void aDeploymentWithAllFourHalvesAnswersOk() throws Exception {
        mvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data.status").value("ok"))
                .andExpect(jsonPath("$.data.db").value(true))
                .andExpect(jsonPath("$.data.redis").value(true))
                .andExpect(jsonPath("$.data.storage").value(true))
                .andExpect(jsonPath("$.data.ai").value(true));
    }

    @Test
    void anAiHalfThatIsGoneSaysSoAndStillAnswers200() throws Exception {
        ai.aiHealthy = false;

        mvc.perform(get("/api/v1/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("degraded"))
                .andExpect(jsonPath("$.data.db").value(true))
                .andExpect(jsonPath("$.data.redis").value(true))
                .andExpect(jsonPath("$.data.storage").value(true))
                .andExpect(jsonPath("$.data.ai").value(false));
    }
}
