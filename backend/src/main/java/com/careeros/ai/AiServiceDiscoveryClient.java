package com.careeros.ai;

import com.careeros.config.AppProperties;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import org.springframework.cloud.client.DefaultServiceInstance;
import org.springframework.cloud.client.ServiceInstance;
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.stereotype.Component;

/**
 * The ai-service as a service, not an address (Epic 85.2).
 *
 * <p>A single engine node stays the default: when {@code AI_SERVICE_INSTANCES} is empty the
 * configured base URL is the one instance, exactly as before. When the operator lists
 * comma-separated origins, each becomes a {@link ServiceInstance} under one service id and
 * Spring Cloud LoadBalancer is free to spread calls across them -- which is what makes a
 * second engine node useful without a proxy in front.
 *
 * <p>Entries are validated here, at the boundary where an operator's environment meets the
 * process, rather than on the first request: a typo should stop the boot with a sentence
 * naming the bad entry, not surface hours later as a mysterious 502. An origin only --
 * scheme, host and optional port -- because every caller appends its own absolute path.
 */
@Component
public class AiServiceDiscoveryClient implements DiscoveryClient {

    public static final String SERVICE_ID = "ai-service";

    private final List<ServiceInstance> instances;

    public AiServiceDiscoveryClient(AppProperties props) {
        this.instances = parse(props.getAiService().getInstances(), props.getAiService().getBaseUrl());
    }

    @Override
    public String description() {
        return "ai-service instances from AI_SERVICE_INSTANCES, else AI_SERVICE_BASE_URL";
    }

    @Override
    public List<ServiceInstance> getInstances(String serviceId) {
        return SERVICE_ID.equalsIgnoreCase(serviceId) ? instances : List.of();
    }

    @Override
    public List<String> getServices() {
        return instances.isEmpty() ? List.of() : List.of(SERVICE_ID);
    }

    /** Every instance's origin, in configured order; the health line asks each in turn. */
    public List<URI> targets() {
        List<URI> targets = new ArrayList<>(instances.size());
        for (ServiceInstance instance : instances) {
            targets.add(instance.getUri());
        }
        return List.copyOf(targets);
    }

    private static List<ServiceInstance> parse(String configured, String baseUrl) {
        List<String> entries = new ArrayList<>();
        if (configured != null && !configured.isBlank()) {
            for (String entry : configured.split(",")) {
                if (!entry.isBlank()) {
                    entries.add(entry.trim());
                }
            }
        }
        if (entries.isEmpty()) {
            entries.add(baseUrl);
        }
        List<ServiceInstance> parsed = new ArrayList<>(entries.size());
        for (int index = 0; index < entries.size(); index++) {
            parsed.add(parseOne(entries.get(index), index));
        }
        return List.copyOf(parsed);
    }

    private static ServiceInstance parseOne(String value, int index) {
        URI uri;
        try {
            uri = URI.create(value);
        } catch (IllegalArgumentException e) {
            throw invalid(value, e);
        }
        String scheme = uri.getScheme();
        boolean http = "http".equalsIgnoreCase(scheme);
        boolean https = "https".equalsIgnoreCase(scheme);
        String path = uri.getPath();
        boolean originOnly = path == null || path.isEmpty() || "/".equals(path);
        if (uri.getHost() == null || !(http || https) || !originOnly
                || uri.getQuery() != null || uri.getFragment() != null || uri.getUserInfo() != null) {
            throw invalid(value, null);
        }
        int port = uri.getPort() > 0 ? uri.getPort() : (https ? 443 : 80);
        return new DefaultServiceInstance(SERVICE_ID + "-" + index, SERVICE_ID,
                uri.getHost(), port, https);
    }

    private static IllegalStateException invalid(String value, Exception cause) {
        String message = "AI_SERVICE_INSTANCES entry is not an absolute http(s) origin: " + value;
        return cause == null ? new IllegalStateException(message) : new IllegalStateException(message, cause);
    }
}
