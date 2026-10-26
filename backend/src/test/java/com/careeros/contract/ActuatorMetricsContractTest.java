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
 *
 * <p>Every claim here is read from a file, so every claim is also about the bytes that file
 * arrives in: measured 2026-10-26, a CRLF rendering of the yml satisfies the exposure pin and
 * defeats the indicator pin, because only the second pattern asks for a newline between two
 * lines. That is not a corner case here -- {@code core.autocrlf=true} with no
 * {@code .gitattributes} in the repo hands a CRLF tree to every fresh Windows checkout and to
 * every plane unpacked from {@code git archive}.
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
        exposurePins(read(APPLICATION_YML));
    }

    /**
     * The same two pins read off a CRLF rendering of the same bytes. The redis pin carries a
     * literal newline inside its pattern, so on {@code \r\n} it does not match while the include
     * pin does: the case is red for a reason that has nothing to do with what the yml declares.
     * That is not hypothetical -- {@code core.autocrlf=true} with no {@code .gitattributes} in the
     * repo hands every fresh Windows checkout, and every plane unpacked from {@code git archive},
     * a CRLF tree, so the shipped suite used to arrive pre-red there.
     */
    @Test
    void theExposurePinsDoNotDependOnTheLineEnding() {
        String lf = read(APPLICATION_YML).replace("\r\n", "\n");
        String crlf = lf.replace("\n", "\r\n");

        assertThat(crlf)
                .as("no CRLF was ever built, so this case graded the file it started with")
                .contains("\r\n");
        assertThat(managementBlock(crlf)).isEqualTo(managementBlock(lf));
        exposurePins(crlf);
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

    /** Both exposure claims, read off whatever line ending the caller brought. */
    private static void exposurePins(String yaml) {
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

    /** The management block only — a stray `include:` elsewhere must not satisfy the pin. */
    private static String managementBlock(String yaml) {
        String text = yaml.replace("\r\n", "\n");
        int start = text.indexOf("management:");
        assertThat(start)
                .as("the management block must exist in application.yml")
                .isGreaterThan(-1);
        String rest = text.substring(start);
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
