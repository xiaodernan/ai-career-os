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
 * The Redis client timeouts are load-bearing configuration, not tuning.
 *
 * <p>Measured against the running stack with the client unconfigured: stopping Redis
 * made {@code GET /api/v1/health} and {@code POST /api/v1/auth/login} fail to answer
 * within 40 seconds, against 0.06s and 0.23s with Redis up. The rate limiter's
 * fail-open branch was correct and did fire — but only after a Redis command timeout,
 * so an outage locked out exactly the users fail-open exists to keep served.
 *
 * <p>Redis backs only the limiter and the health ping, so failing fast costs nothing
 * else. With the 500ms timeouts below, a stopped Redis yields
 * {@code /health -> 200 {"status":"degraded","redis":false}} in 0.51s and
 * {@code /auth/login -> 401} in 1.20s.
 *
 * <p>This test exists so the values cannot be dropped in a refactor and quietly
 * restore an outage that presents as a hang. See {@code docs/SECURITY.md} §3.
 */
class RedisTimeoutContractTest {

    private static final Path APPLICATION_YML =
            Path.of("src", "main", "resources", "application.yml");

    /** A ceiling, not the expected value: anything above this reintroduces the hang. */
    private static final long MAX_ACCEPTABLE_MS = 2_000;

    @Test
    void redisTimeoutsAreConfiguredAndShort() {
        String yaml = read(APPLICATION_YML);
        String redis = redisBlock(yaml);

        assertThat(redis)
                .as("the redis block must still exist in application.yml")
                .isNotBlank();

        assertTimeoutIsShort(redis, "timeout");
        assertTimeoutIsShort(redis, "connect-timeout");
    }

    private static void assertTimeoutIsShort(String redisBlock, String property) {
        Matcher m = Pattern.compile("(?m)^\\s*" + Pattern.quote(property) + ":\\s*(\\S+)")
                .matcher(redisBlock);
        assertThat(m.find())
                .as("spring.data.redis.%s must be set: without it Lettuce's defaults apply "
                        + "and a Redis outage stalls every request instead of failing open",
                        property)
                .isTrue();

        long ms = parseMillis(m.group(1));
        assertThat(ms)
                .as("spring.data.redis.%s is %dms; above %dms a Redis outage stops "
                        + "looking like a degradation and starts looking like a hang",
                        property, ms, MAX_ACCEPTABLE_MS)
                .isLessThanOrEqualTo(MAX_ACCEPTABLE_MS);
    }

    /** Accepts {@code 500ms}, {@code 2s}, or {@code ${VAR:500ms}} — the default matters. */
    private static long parseMillis(String raw) {
        String value = raw;
        if (value.startsWith("${")) {
            int colon = value.indexOf(':');
            assertThat(colon)
                    .as("%s has no default, so an unset environment variable silently "
                            + "falls back to the Lettuce default", raw)
                    .isGreaterThan(-1);
            value = value.substring(colon + 1, value.lastIndexOf('}'));
        }
        Matcher m = Pattern.compile("^(\\d+)(ms|s)?$").matcher(value.trim());
        assertThat(m.matches())
                .as("cannot read a duration from %s", raw)
                .isTrue();
        long n = Long.parseLong(m.group(1));
        return "s".equals(m.group(2)) ? n * 1000 : n;
    }

    /** The redis block only — a `timeout:` elsewhere must not satisfy the assertion. */
    private static String redisBlock(String yaml) {
        StringBuilder out = new StringBuilder();
        boolean inRedis = false;
        for (String line : yaml.split("\n", -1)) {
            if (!inRedis) {
                if (line.trim().equals("redis:")) {
                    inRedis = true;
                    out.append(line).append('\n');
                }
                continue;
            }
            // Ends at the next non-blank line indented no deeper than the `redis:` key.
            // (Matching on "\n  " instead would also match inside "\n      ", cutting the
            // block off at its own first child.)
            if (!line.isBlank() && indentOf(line) <= 2) {
                break;
            }
            out.append(line).append('\n');
        }
        return out.toString();
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
            throw new UncheckedIOException("cannot read " + path.toAbsolutePath(), e);
        }
    }
}
