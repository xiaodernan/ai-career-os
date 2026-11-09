package com.careeros.ai;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.List;
import org.springframework.cloud.client.ServiceInstance;
import org.springframework.cloud.client.loadbalancer.LoadBalancerClient;
import org.springframework.stereotype.Component;

/**
 * Picks a door for each call (Epic 85.2).
 *
 * <p>The choice itself belongs to Spring Cloud LoadBalancer: its blocking client asks the
 * discovery list for {@code ai-service} and applies the configured rule (round-robin by
 * default). This class only turns the chosen instance into an origin the RestClient's
 * request factory can rewrite a path onto, and -- because a bridge must still work when the
 * balancer has no answer for some reason -- falls back to the configured instance list
 * rather than failing on a technicality.
 *
 * <p>The choice is made per request, never cached here: a node that went quiet is skipped
 * by the balancer on the next call, and the circuit breaker above remembers only the
 * exchange, not this routing step.
 */
@Component
public class AiServiceRouter {

    private final LoadBalancerClient loadBalancer;
    private final AiServiceDiscoveryClient discovery;

    public AiServiceRouter(LoadBalancerClient loadBalancer, AiServiceDiscoveryClient discovery) {
        this.loadBalancer = loadBalancer;
        this.discovery = discovery;
    }

    /** The origin (scheme, host and port) the next call should be sent to. */
    public URI base() {
        ServiceInstance chosen = loadBalancer.choose(AiServiceDiscoveryClient.SERVICE_ID);
        return chosen != null ? chosen.getUri() : discovery.targets().get(0);
    }

    /**
     * The doors a stream may knock on, the chosen one first (86.1).
     *
     * <p>An ordinary request can be served by any node because its answer is computed per
     * call. A stream is different: the task it follows lives in the process that started
     * it, and the balancer's next choice need not be that process. The relay therefore
     * asks the chosen door first and then the remaining configured instances, stopping at
     * the one that knows the task; a single-node deployment answers on the first knock.
     */
    public List<URI> doors() {
        List<URI> doors = new ArrayList<>();
        doors.add(base());
        for (URI target : discovery.targets()) {
            if (!doors.contains(target)) {
                doors.add(target);
            }
        }
        return List.copyOf(doors);
    }

    /**
     * Moves a request URI onto the chosen door while keeping the path it was written with.
     * The RestClient is built against a placeholder host, so its call sites keep naming
     * their paths as literals -- which is also what the contract gates read.
     */
    public URI rewrite(URI original) {
        return rewriteTo(base(), original);
    }

    /**
     * The same move onto a door the caller already chose (87.1). The bridge chooses the
     * door before it enters the guard, because the guard now remembers failure per door
     * rather than for the fleet: it has to know which node the exchange is addressed to
     * before the request is built.
     */
    public URI rewriteTo(URI door, URI original) {
        try {
            return new URI(door.getScheme(), null, door.getHost(), door.getPort(),
                    original.getPath(), original.getQuery(), null);
        } catch (URISyntaxException e) {
            throw new IllegalStateException("cannot route " + original + " to " + door, e);
        }
    }
}
