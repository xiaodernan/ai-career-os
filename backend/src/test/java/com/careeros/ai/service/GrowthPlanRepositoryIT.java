package com.careeros.ai.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.ai.entity.GrowthPlan;
import com.careeros.ai.repository.GrowthPlanRepository;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ApiIntegrationTest;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The one round trip 10.4 rests on: a report map goes into the jsonb column and comes back
 * as the same map, and the (user, role) finder finds it. Everything the service test pins
 * with mocks is only true if this is true.
 *
 * <p>The storage override is spelled here as well as on the abstract base: this context
 * loads in its own cache entry, and the property decides which of the two StorageService
 * beans exists — without it both register and the context never comes up.
 */
@TestPropertySource(properties = "app.storage.enabled=false")
class GrowthPlanRepositoryIT extends ApiIntegrationTest {

    @Autowired
    private GrowthPlanRepository plans;

    @Test
    void aReportRoundTripsThroughTheJsonbColumnAndTheFinderFindsIt() throws Exception {
        // The table's foreign key wants a real user, so this registers one — the same
        // per-test account every other integration test uses. The id comes off the
        // register body itself: AuthResponse carries the user beside the tokens.
        MvcResult registered = mvc.perform(post("/api/v1/auth/register")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"gp-" + UUID.randomUUID()
                                + "@example.com\",\"password\":\"Str0ngPassphrase!23\","
                                + "\"displayName\":\"Growth Plan Tester\"}"))
                .andExpect(status().isCreated())
                .andReturn();
        UUID userId = UUID.fromString(MAPPER.readTree(registered.getResponse().getContentAsString())
                .path("data").path("user").path("id").asText());
        GrowthPlan row = new GrowthPlan();
        row.setUserId(userId);
        row.setTargetRole("Senior Backend Engineer (Java)");
        row.setCoverage(0.42);
        row.setReport(Map.of("gap", Map.of("coverage", 0.42), "readiness", Map.of("verdict", "not_ready")));

        plans.saveAndFlush(row);

        GrowthPlan read = plans
                .findFirstByUserIdAndTargetRoleIgnoreCaseOrderByCreatedAtDesc(
                        userId, "senior backend engineer (java)")
                .orElseThrow(() -> new AssertionError("the row just written was not found"));

        assertThat(read.getReport()).isEqualTo(row.getReport());
        assertThat(read.getCoverage()).isEqualTo(0.42);
    }
}
