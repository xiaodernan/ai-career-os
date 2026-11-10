package com.careeros.config;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.boot.actuate.info.Info;
import org.springframework.boot.actuate.info.InfoContributor;
import org.springframework.stereotype.Component;

/**
 * Publishes the ai-service circuit breaker's configured shape on /actuator/info so an
 * authenticated operator can see the resilience policy without scraping source code.
 * No secrets, no runtime state: static configuration values only.
 */
@Component
public class AiServiceResilienceInfoContributor implements InfoContributor {

    @Override
    public void contribute(Info.Builder builder) {
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("slidingWindowSize", AiServiceResilienceConfig.SLIDING_WINDOW_SIZE);
        details.put("minimumNumberOfCalls", AiServiceResilienceConfig.MINIMUM_NUMBER_OF_CALLS);
        details.put("failureRateThreshold", AiServiceResilienceConfig.FAILURE_RATE_THRESHOLD);
        details.put("waitDurationInOpenStateSeconds", AiServiceResilienceConfig.WAIT_DURATION_IN_OPEN_STATE.toSeconds());
        details.put("permittedCallsInHalfOpenState", AiServiceResilienceConfig.PERMITTED_CALLS_IN_HALF_OPEN_STATE);
        builder.withDetail("aiServiceCircuitBreaker", details);
    }
}