package com.careeros.contract;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

/**
 * The Prometheus surface is a wired feature, not an aspiration: DEPLOYMENT.md's monitoring
 * table points scrapers at {@code /actuator/prometheus}, so the three things that keep that
 * true are pinned here — the two registry dependencies, the exposure line that leaves every
 * other actuator endpoint off the wire, and the permitAll pair that lets an unauthenticated
 * scraper through. Removing any one of them is a silent regression the table cannot report.
 */
class ActuatorMetricsContractTest {

    private static final Path POM = Path.of("pom.xml");
    private static final Path APPLICATION_YML =
            Path.of("src", "main", "resources", "application.yml");
    private static final Path SECURITY_CONFIG =
            Path.of("src", "main", "java", "com", "careeros", "config", "SecurityConfig.java");

    @Test
    void thePrometheusRegistryIsOnTheClasspath() {
        String pom = read(POM);

        assertThat(pom).contains("spring-boot-starter-actuator");
        assertThat(pom).contains("micrometer-registry-prometheus");
    }

    @Test
    void onlyHealthAndPrometheusAreExposed() {
        String yaml = read(APPLICATION_YML);
        Matcher include = Pattern.compile("(?m)^\\s*include:\\s*(\\S+)\\s*$")
                .matcher(managementBlock(yaml));

        assertThat(include.find())
                .as("management.endpoints.web.exposure.include must stay declared: without "
                        + "it Spring exposes only /actuator/health and the scrape endpoint "
                        + "silently disappears")
                .isTrue();
        assertThat(include.group(1))
                .as("health and prometheus are the whole observability surface")
                .isEqualTo("health,prometheus");

        Matcher redis = Pattern.compile("(?m)^\\s*redis:\\s*$\\n\\s*enabled:\\s*false")
                .matcher(managementBlock(yaml));
        assertThat(redis.find())
                .as("actuator's redis indicator must stay disabled: it would flip "
                        + "/actuator/health to 503 on a rate-limiter outage, reporting the "
                        + "backend down while /api/v1/health correctly says degraded")
                .isTrue();
    }

    @Test
    void exactlyTheTwoExposedEndpointsArePermitted() {
        String source = read(SECURITY_CONFIG);

        assertThat(source)
                .as("the scraper authenticates with nothing, so the two exposed endpoints "
                        + "must be reachable through the security chain")
                .contains("\"/actuator/health\", \"/actuator/prometheus\"");
        // Defense in depth: the broad form would wave through /actuator/env, /actuator/beans
        // and friends the day someone widens the exposure list.
        assertThat(source).doesNotContain("\"/actuator/**\"");
    }

    /** The management block only — a stray `include:` elsewhere must not satisfy the pin. */
    private static String managementBlock(String yaml) {
        int start = yaml.indexOf("management:");
        assertThat(start)
                .as("the management block must exist in application.yml")
                .isGreaterThan(-1);
        String rest = yaml.substring(start);
        int end = rest.indexOf("\nlogging:");
        return end > -1 ? rest.substring(0, end) : rest;
    }

    private static String read(Path path) {
        try {
            return Files.readString(path);
        } catch (IOException e) {
            throw new UncheckedIOException("cannot read " + path.toAbsolutePath(), e);
        }
    }
}
