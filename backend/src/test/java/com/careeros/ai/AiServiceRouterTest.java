package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.config.AppProperties;
import java.net.URI;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.client.DefaultServiceInstance;
import org.springframework.cloud.client.loadbalancer.LoadBalancerClient;

/**
 * One door per call (Epic 85.2).
 *
 * <p>The balancer owns which instance; what this class owns is asking it again on every
 * call (never pinning the first answer) and turning the chosen instance into an origin a
 * path can be resolved against. When the balancer has no answer -- a single-node run, or a
 * discovery implementation that has not loaded -- the configured list is still a bridge.
 */
class AiServiceRouterTest {

    @Test
    void everyCallAsksTheBalancerAgain() {
        LoadBalancerClient loadBalancer = mock(LoadBalancerClient.class);
        when(loadBalancer.choose(AiServiceDiscoveryClient.SERVICE_ID))
                .thenReturn(instance("http://10.0.0.1:8000"), instance("http://10.0.0.2:8000"));
        AiServiceRouter router = new AiServiceRouter(loadBalancer, discovery("http://localhost:8000", ""));

        assertThat(router.base()).isEqualTo(URI.create("http://10.0.0.1:8000"));
        assertThat(router.base()).isEqualTo(URI.create("http://10.0.0.2:8000"));
        verify(loadBalancer, times(2)).choose(AiServiceDiscoveryClient.SERVICE_ID);
    }

    @Test
    void aBalancerWithNoAnswerFallsBackToTheConfiguredDoor() {
        LoadBalancerClient loadBalancer = mock(LoadBalancerClient.class);
        when(loadBalancer.choose(AiServiceDiscoveryClient.SERVICE_ID)).thenReturn(null);
        AiServiceRouter router = new AiServiceRouter(loadBalancer, discovery("http://localhost:8000", ""));

        assertThat(router.base()).isEqualTo(URI.create("http://localhost:8000"));
    }

    @Test
    void aPathBecomesAnAbsoluteUrlOnTheChosenDoor() {
        LoadBalancerClient loadBalancer = mock(LoadBalancerClient.class);
        when(loadBalancer.choose(AiServiceDiscoveryClient.SERVICE_ID))
                .thenReturn(instance("http://10.0.0.2:8000"));
        AiServiceRouter router = new AiServiceRouter(loadBalancer, discovery("http://localhost:8000", ""));

        assertThat(router.url("/internal/features/match"))
                .isEqualTo(URI.create("http://10.0.0.2:8000/internal/features/match"));
    }

    private static DefaultServiceInstance instance(String origin) {
        URI uri = URI.create(origin);
        return new DefaultServiceInstance(uri.getHost(), AiServiceDiscoveryClient.SERVICE_ID,
                uri.getHost(), uri.getPort(), false);
    }

    private static AiServiceDiscoveryClient discovery(String baseUrl, String instances) {
        AppProperties props = new AppProperties();
        props.getAiService().setBaseUrl(baseUrl);
        props.getAiService().setInstances(instances);
        return new AiServiceDiscoveryClient(props);
    }
}
