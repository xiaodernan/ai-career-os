package com.careeros.discovery;

import static org.assertj.core.api.Assertions.assertThat;

import com.netflix.appinfo.DataCenterInfo;
import com.netflix.appinfo.InstanceInfo;
import com.netflix.eureka.registry.PeerAwareInstanceRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

/**
 * The registry has to do two things before the gateway can trust it: answer that it is
 * alive, and treat a registered instance as an instance (Epic 98).
 *
 * <p>The registration goes through {@link PeerAwareInstanceRegistry} rather than a hand
 * written HTTP body. The HTTP registration endpoint is the same code path -- it hands
 * the decoded {@code InstanceInfo} to this registry -- while a hand-written body would
 * test this test's JSON spelling instead of the registry's bookkeeping. The HTTP views
 * are still read: the application list and the dashboard are what an operator uses.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
        "eureka.server.response-cache-update-interval-ms=100"
})
class DiscoveryApplicationTests {

    private static final String APP = "BACKEND";

    @Autowired
    private TestRestTemplate rest;

    @Autowired
    private PeerAwareInstanceRegistry registry;

    @Autowired
    private org.springframework.core.env.Environment env;

    @Test
    void aLoneRegistryKeepsTheClientOff() {
        // Epic 113's other half: the peer profile turns the client on, so the
        // default profile must be the one that keeps it off. A lone registry
        // registering with itself would only describe a map it already holds.
        assertThat(env.getProperty("eureka.client.register-with-eureka", Boolean.class)).isFalse();
        assertThat(env.getProperty("eureka.client.fetch-registry", Boolean.class)).isFalse();
        assertThat(env.getProperty("eureka.server.enable-self-preservation", Boolean.class))
                .as("peer-less, the registry cannot tell a dead service from a network "
                        + "hiccup -- so it must keep evicting")
                .isFalse();
    }

    @Test
    void answersHealthy() {
        ResponseEntity<String> health = rest.getForEntity("/actuator/health", String.class);

        assertThat(health.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(health.getBody()).contains("\"status\":\"UP\"");
    }

    @Test
    void publishesAnApplicationListEvenWhenItIsEmpty() throws Exception {
        // A caller reading the list must get the shape it expects, not a 404, before the
        // first service has registered: the edge polls this endpoint from its first tick.
        ResponseEntity<String> apps = rest.getForEntity("/eureka/apps", String.class);

        assertThat(apps.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(apps.getBody()).contains("applications");
    }

    @Test
    void keepsWhatIsRegisteredAndForgetsWhatIsWithdrawn() throws Exception {
        InstanceInfo instance = InstanceInfo.Builder.newBuilder()
                .setAppName(APP)
                .setInstanceId("backend-1")
                .setHostName("127.0.0.1")
                .setIPAddr("127.0.0.1")
                .setPort(8080)
                .setVIPAddress("backend")
                .setSecureVIPAddress("backend")
                .setDataCenterInfo((DataCenterInfo) () -> DataCenterInfo.Name.MyOwn)
                .setStatus(InstanceInfo.InstanceStatus.UP)
                .build();

        registry.register(instance, false);
        try {
            assertThat(registry.getApplication(APP)).isNotNull();
            assertThat(registry.getApplication(APP).getInstances())
                    .extracting(InstanceInfo::getInstanceId)
                    .contains("backend-1");
            assertThat(registry.getApplication(APP).getInstances())
                    .extracting(InstanceInfo::getStatus)
                    .contains(InstanceInfo.InstanceStatus.UP);

            ResponseEntity<String> apps = rest.getForEntity("/eureka/apps", String.class);
            assertThat(apps.getStatusCode()).isEqualTo(HttpStatus.OK);
            assertThat(apps.getBody())
                    .as("the list an operator reads is the registry's own answer")
                    .contains("backend-1");
        } finally {
            registry.cancel(APP, "backend-1", false);
        }

        assertThat(registry.getApplication(APP)).isNull();
    }

    @Test
    void rendersTheOperatorsDashboard() {
        ResponseEntity<String> dashboard = rest.getForEntity("/", String.class);

        assertThat(dashboard.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(dashboard.getBody()).containsIgnoringCase("eureka");
    }
}
