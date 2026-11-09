package com.careeros.system;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.cloud.client.ServiceInstance;
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.stereotype.Service;

/**
 * What the backend can see of its own fleet (Epic 100).
 *
 * <p>The answer comes from the same `DiscoveryClient` the load balancer uses, so the
 * page describes the routing table instead of a second inventory that drifts from it.
 * In the default deployment that client is {@code AiServiceDiscoveryClient} and the list
 * is the configured engine origins; with the `eureka` profile it is the composite the
 * registry feeds.
 *
 * <p>The registry mode is read from the active profile rather than inferred from which
 * client bean happens to be primary: the profile is the switch an operator set, and a
 * page that guesses can disagree with the deployment's own configuration.
 */
@Service
public class ServiceTopologyService {

    static final String EUREKA_PROFILE = "eureka";

    private final DiscoveryClient discoveryClient;
    private final Environment environment;

    public ServiceTopologyService(DiscoveryClient discoveryClient, Environment environment) {
        this.discoveryClient = discoveryClient;
        this.environment = environment;
    }

    public Map<String, Object> report() {
        List<Map<String, Object>> services = discoveryClient.getServices().stream()
                .distinct()
                .sorted(String.CASE_INSENSITIVE_ORDER)
                .map(this::row)
                .toList();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("registry", environment.acceptsProfiles(Profiles.of(EUREKA_PROFILE))
                ? "eureka"
                : "configuration");
        body.put("services", services);
        return body;
    }

    private Map<String, Object> row(String name) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("name", name);
        row.put("instances", discoveryClient.getInstances(name).stream()
                .map(this::instance)
                .toList());
        return row;
    }

    private Map<String, Object> instance(ServiceInstance instance) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("instanceId", instance.getInstanceId() == null
                ? instance.getHost() + ":" + instance.getPort()
                : instance.getInstanceId());
        row.put("uri", instance.getUri().toString());
        return row;
    }
}
