package com.careeros.ai;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.config.AppProperties;
import java.net.URI;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.client.ServiceInstance;

/**
 * The configured engine doors (Epic 85.2).
 *
 * <p>Two rules matter: a single-node run must keep working without anyone learning a new
 * setting (the base URL is the only instance), and a typo in the multi-node list must stop
 * the boot with the offending entry in the sentence -- not become a 502 hours later.
 */
class AiServiceDiscoveryClientTest {

    @Test
    void theBaseUrlIsTheOneInstanceWhenNobodyListsMore() {
        AiServiceDiscoveryClient discovery = discovery("http://localhost:8000", "");

        assertThat(discovery.getServices()).containsExactly("ai-service");
        List<ServiceInstance> instances = discovery.getInstances("ai-service");
        assertThat(instances).hasSize(1);
        assertThat(instances.get(0).getHost()).isEqualTo("localhost");
        assertThat(instances.get(0).getPort()).isEqualTo(8000);
        assertThat(instances.get(0).isSecure()).isFalse();
        assertThat(discovery.targets()).containsExactly(URI.create("http://localhost:8000"));
    }

    @Test
    void aCommaSeparatedListBecomesThatManyDoorsInOrder() {
        AiServiceDiscoveryClient discovery = discovery("http://localhost:8000",
                " http://10.0.0.1:8000 , https://engine.internal ");

        List<ServiceInstance> instances = discovery.getInstances("ai-service");
        assertThat(instances).hasSize(2);
        assertThat(discovery.targets()).containsExactly(
                URI.create("http://10.0.0.1:8000"),
                URI.create("https://engine.internal:443"));
        assertThat(instances.get(1).getPort()).isEqualTo(443);
        assertThat(instances.get(1).isSecure()).isTrue();
    }

    @Test
    void anotherServiceIsNotTheEngine() {
        assertThat(discovery("http://localhost:8000", "").getInstances("postgres")).isEmpty();
    }

    @Test
    void aTypoStopsTheBootWithTheEntryInTheSentence() {
        assertThatThrownBy(() -> discovery("http://localhost:8000", "http://10.0.0.1:8000,engine.internal:8000"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("engine.internal:8000");
    }

    @Test
    void anEntryThatIsNotAnOriginIsRefusedRatherThanSilentlyTrimmed() {
        assertThatThrownBy(() -> discovery("http://localhost:8000", "http://10.0.0.1:8000/internal"))
                .isInstanceOf(IllegalStateException.class);
    }

    private static AiServiceDiscoveryClient discovery(String baseUrl, String instances) {
        AppProperties props = new AppProperties();
        props.getAiService().setBaseUrl(baseUrl);
        props.getAiService().setInstances(instances);
        return new AiServiceDiscoveryClient(props);
    }
}
