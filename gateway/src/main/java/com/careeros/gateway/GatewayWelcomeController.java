package com.careeros.gateway;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * What answers when someone opens the front door (Epic 92).
 *
 * <p>A proxy's root is otherwise a 404, which reads as "wrong address" to a person and
 * as "unhealthy" to a naive probe. This says what the process is, where the API lives
 * and where its health line is -- three facts an operator needs before reading a log.
 */
@RestController
public class GatewayWelcomeController {

    @GetMapping("/")
    public Map<String, String> welcome() {
        return Map.of(
                "service", "career-os-gateway",
                "status", "ok",
                "api", "/api/**",
                "health", "/actuator/health");
    }
}
