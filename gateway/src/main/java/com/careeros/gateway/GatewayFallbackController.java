package com.careeros.gateway;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The sentence the edge answers with when nothing is behind the door (Epic 88.2).
 *
 * <p>It is served by this process and names no upstream, so it still works when the
 * backend -- or its whole host -- is gone. The shape mirrors the backend's error
 * envelope's two most useful fields without pretending to be a domain error: the
 * browser needs a code it can branch on and a sentence it can show, and neither should
 * be a stack trace. The code is a franchise of the browser's i18n table, which
 * renders it in the reader's language.
 */
@RestController
public class GatewayFallbackController {

    @RequestMapping("/_fallback/backend")
    public ResponseEntity<Map<String, String>> backendUnavailable() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of(
                        "error", "BACKEND_UNAVAILABLE",
                        "message", "The domain backend is not answering."));
    }
}
