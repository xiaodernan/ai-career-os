package com.careeros.gateway;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.cloud.client.discovery.simple.SimpleDiscoveryProperties;
import org.springframework.cloud.netflix.eureka.EurekaDiscoveryClient;
import org.springframework.test.context.ActiveProfiles;

/**
 * The `eureka` profile must replace the configuration list, not sit beside it (Epic 98).
 *
 * <p>Two discovery clients on one classpath are merged by Spring Cloud's composite. If
 * the profile only turned Eureka on, the simple list would keep contributing the laptop
 * address and roughly half the edge's load-balancing decisions would ignore the
 * registry -- a bug that looks like flaky routing and never fails a unit test. This test
 * asserts the profile is exclusive: Eureka is present, the simple list is empty, and the
 * only answer for `backend` is the registry's (which is empty here, because no service
 * registered).
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "eureka.client.fetch-registry=false",
        "eureka.client.register-with-eureka=false"
})
@ActiveProfiles("eureka")
class GatewayRegistryProfileTest {

    @Autowired
    private DiscoveryClient discoveryClient;

    @Autowired
    private SimpleDiscoveryProperties simple;

    @Autowired
    private EurekaDiscoveryClient eurekaDiscoveryClient;

    @Test
    void theRegistryIsTheOnlyAnswerInTheRegistryProfile() {
        assertThat(eurekaDiscoveryClient)
                .as("the profile's whole purpose is to put Eureka in the composite")
                .isNotNull();
        assertThat(simple.getInstances().getOrDefault("backend", List.of()))
                .as("a configured address left beside the registry is a second answer "
                        + "the operator cannot see")
                .isEmpty();
        assertThat(discoveryClient.getInstances("backend")).isEmpty();
    }
}
