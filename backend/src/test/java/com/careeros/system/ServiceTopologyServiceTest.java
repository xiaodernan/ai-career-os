package com.careeros.system;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.client.DefaultServiceInstance;
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.mock.env.MockEnvironment;

/**
 * The topology page must describe the routing table, not a second inventory (Epic 100).
 *
 * <p>The service list arrives from the same `DiscoveryClient` the load balancer reads.
 * Sorting is part of the contract: two reads a minute apart should differ only when the
 * fleet changed, not when a hash map iterated in another order.
 */
class ServiceTopologyServiceTest {

    private final DiscoveryClient discovery = mock(DiscoveryClient.class);

    @Test
    void listsEveryServiceInAStableOrderWithItsInstances() {
        when(discovery.getServices()).thenReturn(List.of("backend", "ai-service"));
        when(discovery.getInstances("backend")).thenReturn(List.of(
                new DefaultServiceInstance("backend-1", "backend", "10.0.0.2", 8080, false),
                new DefaultServiceInstance("backend-2", "backend", "10.0.0.3", 8080, false)));
        when(discovery.getInstances("ai-service")).thenReturn(List.of(
                new DefaultServiceInstance("ai-1", "ai-service", "10.0.0.4", 8000, false)));

        Map<String, Object> report = new ServiceTopologyService(discovery, new MockEnvironment())
                .report();

        assertThat(report.get("registry")).isEqualTo("configuration");
        List<Map<String, Object>> services = rows(report.get("services"));
        assertThat(services).extracting(row -> row.get("name"))
                .containsExactly("ai-service", "backend");

        List<Map<String, Object>> instances = rows(services.get(1).get("instances"));
        assertThat(instances).extracting(row -> row.get("instanceId"))
                .containsExactly("backend-1", "backend-2");
        assertThat(instances).extracting(row -> row.get("uri"))
                .containsExactly("http://10.0.0.2:8080", "http://10.0.0.3:8080");
    }

    @Test
    void namesTheRegistryWhenItsProfileIsActive() {
        when(discovery.getServices()).thenReturn(List.of());
        MockEnvironment environment = new MockEnvironment();
        environment.setActiveProfiles(ServiceTopologyService.EUREKA_PROFILE);

        Map<String, Object> report = new ServiceTopologyService(discovery, environment).report();

        assertThat(report.get("registry")).isEqualTo("eureka");
        assertThat(rows(report.get("services"))).isEmpty();
    }

    @Test
    void anInstanceWithoutAnIdIsNamedByItsAddress() {
        when(discovery.getServices()).thenReturn(List.of("ai-service"));
        when(discovery.getInstances("ai-service")).thenReturn(List.of(
                new DefaultServiceInstance(null, "ai-service", "127.0.0.1", 8000, false)));

        List<Map<String, Object>> services = rows(new ServiceTopologyService(
                discovery, new MockEnvironment()).report().get("services"));
        List<Map<String, Object>> instances = rows(services.get(0).get("instances"));

        assertThat(instances.get(0).get("instanceId")).isEqualTo("127.0.0.1:8000");
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> rows(Object value) {
        return (List<Map<String, Object>>) value;
    }
}
