package com.careeros.admin;

import com.careeros.ai.AiServiceClient;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Epic 320 -- the overseer's own analyst, through the ai-service.
 *
 * The deterministic counsel above this route is honest arithmetic over the same rows
 * the ledger renders; the LLM pass is the second read \u2014 the one that notices what a
 * rule cannot name. The snapshot ride from the browser is exactly what the admin page
 * already fetches to draw itself: the by-kind cache table, the weekly series, the
 * stat tiles, the attention halves, the funnel. Nothing named, nothing per user.
 *
 * The call is 30-second cached -- a full LLM pass per admin-page refresh is a bill
 * nobody wants -- and the provider is called with the shared internal token exactly
 * like every other /internal/* route. When the relay is down the answer is {empty: true}
 * not a mocked voice: the admin page renders nothing rather than "AI says hello".
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminCounselController {

    private final AiServiceClient ai;
    private final AdminCache cache;
    private static final UUID SYSTEM_USER = new UUID(0L, 0L);

    public AdminCounselController(AiServiceClient ai, AdminCache cache) {
        this.ai = ai;
        this.cache = cache;
    }

    @PostMapping("/counsel-llm")
    @org.springframework.transaction.annotation.Transactional(readOnly = true)
    public Map<String, Object> counselLlm(@RequestBody(required = false) Map<String, Object> body) {
        Object raw = body == null ? null : body.get("snapshot");
        Map<String, Object> snapshot = raw instanceof Map<?, ?> rawMap
                ? recastMap(rawMap) : (body == null ? Map.of() : body);
        return cache.get("counsel-llm").orElseGet(() -> {
            Map<String, Object> out;
            try {
                out = ai.counsel(snapshot, SYSTEM_USER);
                if (out == null || out.isEmpty()) {
                    out = Map.of("summary", "", "actions", java.util.List.of(),
                            "risks", java.util.List.of(), "actions_dropped", 0,
                            "risks_dropped", 0, "empty", true);
                } else {
                    out = new LinkedHashMap<>(out);
                    out.put("empty", false);
                }
            } catch (Exception e) {
                out = Map.of("summary", "", "actions", java.util.List.of(),
                        "risks", java.util.List.of(), "actions_dropped", 0,
                        "risks_dropped", 0, "empty", true);
            }
            cache.put("counsel-llm", out);
            return out;
        });
    }

    private static Map<String, Object> recastMap(Map<?, ?> raw) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : raw.entrySet()) {
            if (e.getKey() instanceof String k) out.put(k, e.getValue());
        }
        return out;
    }
}
