package com.careeros.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;

/**
 * The ceiling holds by construction: the limiter's decision is ONE atomic script call —
 * one key, five arguments — not a read-count-add spread over four round trips. That split
 * was the race: two replicas could both read {@code live < limit} and both add, exceeding
 * the configured ceiling under the very concurrency it exists to bound. A future refactor
 * back to {@code opsForZSet().count(...)} reintroduces the race and reddens this suite.
 */
class RedisSlidingWindowAtomicityTest {

    @Test
    void theCeilingIsTakenByOneAtomicScriptCall() {
        CapturingRedis redis = new CapturingRedis(1L);
        RedisSlidingWindowRateLimiter limiter = new RedisSlidingWindowRateLimiter(redis);

        assertThat(limiter.tryAcquire("rl:user:1", 5, Duration.ofMinutes(1))).isTrue();

        assertThat(redis.calls).isEqualTo(1);
        assertThat(redis.keys).containsExactly("rl:user:1");
        assertThat(redis.arguments).hasSize(5);
        // cutoff, now, limit, unique member, ttl — in that order
        assertThat(String.valueOf(redis.arguments[2])).isEqualTo("5");
        assertThat(String.valueOf(redis.arguments[4])).isEqualTo("65000");
        assertThat(String.valueOf(redis.arguments[0])).matches("\\d{10,}"); // cutoff
        assertThat(String.valueOf(redis.arguments[1])).matches("\\d{10,}"); // now
        assertThat(String.valueOf(redis.arguments[3])).contains(":"); // now:uuid
        assertThat(RedisSlidingWindowRateLimiter.SCRIPT)
                .contains("ZREMRANGEBYSCORE", "ZCARD", "ZADD", "PEXPIRE", "return 0", "return 1");
        // Five redis.call invocations (trim, count, refusal-TTL, add, admission-TTL) => 6 parts.
        assertThat(RedisSlidingWindowRateLimiter.SCRIPT.split("redis.call", -1)).hasSize(6);
    }

    @Test
    void aRefusalIsNotAdmitted() {
        assertThat(new RedisSlidingWindowRateLimiter(new CapturingRedis(0L))
                .tryAcquire("k", 5, Duration.ofMinutes(1))).isFalse();
    }

    @Test
    void anAdmissionIsAdmitted() {
        assertThat(new RedisSlidingWindowRateLimiter(new CapturingRedis(1L))
                .tryAcquire("k", 5, Duration.ofMinutes(1))).isTrue();
    }

    @Test
    void anEmptyScriptAnswerFailsOpen() {
        // Backend posture: an unknown answer admits rather than locks a user out.
        assertThat(new RedisSlidingWindowRateLimiter(new CapturingRedis(null))
                .tryAcquire("k", 5, Duration.ofMinutes(1))).isTrue();
    }

    @Test
    void aRedisOutageFailsOpen() {
        CapturingRedis redis = new CapturingRedis(1L) {
            @Override
            public <T> T execute(RedisScript<T> script, List<String> keys, Object... args) {
                throw new RuntimeException("connection refused");
            }
        };
        assertThat(new RedisSlidingWindowRateLimiter(redis)
                .tryAcquire("k", 5, Duration.ofMinutes(1))).isTrue();
    }

    @Test
    void twoCallsInOneInstantGetDifferentMembers() {
        CapturingRedis redis = new CapturingRedis(1L);
        RedisSlidingWindowRateLimiter limiter = new RedisSlidingWindowRateLimiter(redis);
        limiter.tryAcquire("k", 5, Duration.ofMinutes(1));
        Object first = redis.arguments[3];
        limiter.tryAcquire("k", 5, Duration.ofMinutes(1));
        Object second = redis.arguments[3];
        // Each admission must add a distinct member, or a same-millisecond second caller
        // would overwrite the first in the ZSET and silently pass the ceiling again.
        assertThat(String.valueOf(first)).isNotEqualTo(String.valueOf(second));
        assertThat(redis.calls).isEqualTo(2);
    }

    /** A template that records what the limiter asked it to run and answers with one value. */
    static class CapturingRedis extends StringRedisTemplate {
        int calls;
        List<String> keys;
        Object[] arguments;
        private final Long answer;

        CapturingRedis(Long answer) {
            super(mock(RedisConnectionFactory.class));
            this.answer = answer;
        }

        @Override
        @SuppressWarnings("unchecked")
        public <T> T execute(RedisScript<T> script, List<String> keys, Object... args) {
            calls++;
            this.keys = keys;
            this.arguments = args;
            return (T) answer;
        }
    }
}
