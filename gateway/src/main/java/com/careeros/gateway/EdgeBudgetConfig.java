package com.careeros.gateway;

import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;

/**
 * The shared budget exists only when an operator asked for it (Epic 120).
 *
 * <p>No Redis bean is depending on at start-up: the connection factory is lazy, so a
 * laptop with no Redis keeps the in-process edge it had before, and the flag is the one
 * thing that changes the answer. The condition is on the property rather than on the
 * presence of a template, because a template is always present once the starter is on
 * the classpath -- the property is the decision, the template is only the plumbing.
 */
@Configuration
class EdgeBudgetConfig {

    @Bean
    @ConditionalOnProperty(name = "GATEWAY_RATE_LIMIT_REDIS", havingValue = "true")
    EdgeBudget sharedEdgeBudget(
            ReactiveStringRedisTemplate redis,
            @Value("${GATEWAY_RATE_LIMIT_PER_MINUTE:1200}") int tokensPerPeriod,
            @Value("${GATEWAY_RATE_LIMIT_PERIOD:60s}") Duration period) {
        return new RedisBudget(redis, tokensPerPeriod, period);
    }
}
