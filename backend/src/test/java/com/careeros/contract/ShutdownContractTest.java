package com.careeros.contract;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

/**
 * A redeploy finishes the request it already took (roadmap 39.4).
 *
 * <p>{@code server.shutdown} defaults to {@code immediate}: closing the context closes
 * the connector under requests that were already being answered, and the caller sees a
 * reset it did not cause. Set to {@code graceful}, the server stops accepting new
 * connections and lets the active ones finish -- bounded by
 * {@code spring.lifecycle.timeout-per-shutdown-phase}, so one stuck request cannot hold
 * a redeploy forever. The schedulers are not detached workers; they stop with the
 * context after that drain.
 *
 * <p>Docker adds a second, earlier bound: {@code docker stop} sends SIGKILL when the
 * grace period expires, and the default is 10 seconds -- short enough to kill the JVM
 * while its own 30-second phase is still draining. Both compose files therefore set
 * {@code stop_grace_period} above the phase timeout, and this test refuses a stack that
 * undercuts the JVM. See {@code docs/RUNBOOK.md}, "A redeploy finishes what it started".
 */
class ShutdownContractTest {

    private static final Path APPLICATION_YML =
            Path.of("src", "main", "resources", "application.yml");
    private static final List<Path> COMPOSE_FILES =
            List.of(Path.of("..", "docker-compose.yml"), Path.of("..", "docker-compose.prod.yml"));

    /** Anything above this is not a drain bound; it is a redeploy that never ends. */
    private static final long MAX_PHASE_MS = 120_000;

    /** Docker must kill after the JVM has cut, never at the same instant. */
    private static final long GRACE_MARGIN_MS = 5_000;

    @Test
    void theServerDrainsInsteadOfCuttingAndTheDrainIsBounded() {
        String yaml = read(APPLICATION_YML);

        assertThat(property(block(yaml, "server"), "shutdown"))
                .as("application.yml's server.shutdown must be graceful: immediate cuts "
                        + "requests that were already being answered")
                .isEqualTo("graceful");

        String lifecycle = block(block(yaml, "spring"), "lifecycle");
        String raw = property(lifecycle, "timeout-per-shutdown-phase");
        assertThat(raw)
                .as("spring.lifecycle.timeout-per-shutdown-phase must be set: graceful "
                        + "without a bound lets one stuck request hold a redeploy forever")
                .isNotNull();
        long phase = parseMillis(raw, "spring.lifecycle.timeout-per-shutdown-phase");
        assertThat(phase)
                .as("a %dms shutdown phase is not a bound worth having; the accepted "
                        + "window is 1ms..%dms", phase, MAX_PHASE_MS)
                .isBetween(1L, MAX_PHASE_MS);
    }

    @Test
    void dockerWaitsLongerThanTheJvmDoes() {
        long phase = parseMillis(
                property(block(block(read(APPLICATION_YML), "spring"), "lifecycle"),
                        "timeout-per-shutdown-phase"),
                "spring.lifecycle.timeout-per-shutdown-phase");

        for (Path compose : COMPOSE_FILES) {
            String backend = block(read(compose), "backend");
            String raw = property(backend, "stop_grace_period");
            assertThat(raw)
                    .as("%s: the backend service must set stop_grace_period; Docker's "
                            + "10-second default SIGKILLs the JVM while the graceful phase "
                            + "is still draining", compose)
                    .isNotNull();
            long grace = parseMillis(raw, compose + " backend.stop_grace_period");
            assertThat(grace)
                    .as("%s waits %dms before SIGKILL, but the JVM may spend up to %dms "
                            + "draining plus its own exit time; the compose grace must "
                            + "exceed the phase timeout by at least %dms",
                            compose, grace, phase, GRACE_MARGIN_MS)
                    .isGreaterThanOrEqualTo(phase + GRACE_MARGIN_MS);
        }
    }

    /** The direct children of a top-level (or nested) {@code key:} line. */
    private static String block(String yaml, String key) {
        String[] lines = yaml.split("\n", -1);
        int start = -1;
        int indent = -1;
        for (int i = 0; i < lines.length; i++) {
            if (lines[i].trim().equals(key + ":")) {
                start = i;
                indent = indentOf(lines[i]);
                break;
            }
        }
        assertThat(start)
                .as("no %s: block to read (a rename must update this contract, not "
                        + "silently drop the pin)", key)
                .isGreaterThanOrEqualTo(0);

        StringBuilder out = new StringBuilder();
        for (int i = start + 1; i < lines.length; i++) {
            String line = lines[i];
            if (!line.isBlank() && indentOf(line) <= indent) {
                break;
            }
            out.append(line).append('\n');
        }
        return out.toString();
    }

    private static String property(String block, String name) {
        Matcher m = Pattern.compile("(?m)^[ \t]*" + Pattern.quote(name) + ":[ \t]*(\\S+)")
                .matcher(block);
        return m.find() ? m.group(1) : null;
    }

    private static long parseMillis(String raw, String what) {
        assertThat(raw).as("%s is missing", what).isNotNull();
        Matcher m = Pattern.compile("^(\\d+)(ms|s|m)?$").matcher(raw.trim());
        assertThat(m.matches())
                .as("%s is %s; this test reads a plain duration (30s, 40s) so it can "
                        + "compare the two bounds", what, raw)
                .isTrue();
        long n = Long.parseLong(m.group(1));
        String unit = m.group(2) == null ? "ms" : m.group(2);
        return switch (unit) {
            case "ms" -> n;
            case "s" -> n * 1_000;
            case "m" -> n * 60_000;
            default -> throw new IllegalStateException(unit);
        };
    }

    private static int indentOf(String line) {
        int i = 0;
        while (i < line.length() && line.charAt(i) == ' ') {
            i++;
        }
        return i;
    }

    private static String read(Path path) {
        try {
            return Files.readString(path);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
