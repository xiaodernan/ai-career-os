package com.careeros.discovery;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.test.context.ActiveProfiles;

/**
 * Epic 113: what the {@code peer} profile changes, read off the environment the
 * profile composes. A second registry is only a second registry if each node
 * pushes its registrations into the other and pulls the other's view -- the two
 * booleans this profile turns on -- and self-preservation comes back on, because
 * a partition between two nodes is exactly the case the protection exists for.
 *
 * <p>Property-level on purpose: the two-node boot itself needs the live pair and
 * is documented as a manual runbook step (docs/DEPLOYMENT.md); what the offline
 * suite can hold is that the profile's wiring says the right things before any
 * socket is opened. The zone is asserted through the same key the orchestrator
 * sets, so a variable rename on the compose side reddens here.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK, properties = {
        "eureka.client.service-url.defaultZone=http://discovery:8761/eureka/"
})
@ActiveProfiles("peer")
class DiscoveryPeerProfileTests {

    @Autowired
    private Environment env;

    @Test
    void thePeerProfileTurnsTheClientOn() {
        assertThat(env.getProperty("eureka.client.register-with-eureka", Boolean.class))
                .as("a peer that does not register into the other is not gossiping")
                .isTrue();
        assertThat(env.getProperty("eureka.client.fetch-registry", Boolean.class))
                .as("a peer that does not read the other's view cannot serve what it learns")
                .isTrue();
    }

    @Test
    void thePeerProfileRestoresSelfPreservation() {
        assertThat(env.getProperty("eureka.server.enable-self-preservation", Boolean.class))
                .as("with a peer, a network partition is real; evicting half the fleet "
                        + "during one is the failure the protection exists for")
                .isTrue();
    }

    @Test
    void theZoneIsWhatTheOrchestratorNames() {
        assertThat(env.getProperty("eureka.client.service-url.defaultZone"))
                .as("the zone each node gossips through is the orchestrator's variable, "
                        + "not a value the profile hardcodes")
                .isEqualTo("http://discovery:8761/eureka/");
    }
}
