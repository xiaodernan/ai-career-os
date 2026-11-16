package com.careeros.attention.web;

import com.careeros.attention.entity.AttentionEvent;
import com.careeros.attention.repository.AttentionRepository;
import com.careeros.attention.service.AttentionAdminService;
import com.careeros.common.AuthUser;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The attention door (Epic 267).
 *
 * <p>The browser posts, the server records, the admin reads aggregates. No per-user rows
 * cross the wire. The write side intentionally has no auth wall: an unauthenticated
 * landing on the landing page still matters (someone who never registered), and the
 * value is the path — never the user's content.
 *
 * <p>Epic 289 adds POST/DELETE /admin/simulate — the overseer's synthetic week: a
 * bounded, tagged generator of the same three row shapes the browser writes, journey
 * always "synthetic", never a signed user, always wipeable.
 */
@RestController
@RequestMapping("/api/v1")
public class AttentionController {

    private final AttentionRepository repo;
    private final AttentionAdminService admin;
    private final boolean enabled;

    public AttentionController(AttentionRepository repo,
                                AttentionAdminService admin,
                                @Value("${careeros.attention.enabled:true}") boolean enabled) {
        this.repo = repo;
        this.admin = admin;
        this.enabled = enabled;
    }

    public record AttentionRequest(String journey, String path, String event, String value) {
    }

    /** POST /api/v1/telemetry/attention — the one writer, idempotent by landing shape. */
    @PostMapping("/telemetry/attention")
    public Map<String, Object> record(@RequestBody(required = false) AttentionRequest body) {
        if (!enabled || body == null || body.path() == null) {
            return Map.of("recorded", false);
        }
        String path = body.path().trim();
        // The admin door is a measurement instrument; nothing goes in the database that describes it.
        if (path.startsWith("/admin")) {
            return Map.of("recorded", false);
        }
        String event = body.event() == null ? "land" : body.event().trim();
        if (!Set.of("land", "dwell", "act").contains(event)) {
            return Map.of("recorded", false);
        }
        String value = body.value() == null ? null : body.value().trim();
        if (value != null && value.length() > 200) {
            value = value.substring(0, 200);
        }
        // Optional auth: a logged-out landing is just counted as anonymous.
        UUID userId = null;
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof AuthUser user) {
            userId = user.id();
        }
        AttentionEvent saved = repo.save(new AttentionEvent(
                userId,
                body.journey() == null ? "app" : body.journey().trim(),
                path.length() > 500 ? path.substring(0, 500) : path,
                event,
                value));
        return Map.of("recorded", true, "id", saved.getId().toString());
    }

    /** GET /api/v1/admin/attention — the aggregate, counts only. */
    @GetMapping("/admin/attention")
    public Map<String, Object> attention() {
        return admin.summary();
    }

    /** POST /api/v1/admin/simulate — seed a bounded synthetic week; the overseer's rig, not a visitor. */
    @PostMapping("/admin/simulate")
    public Map<String, Object> simulate(@RequestBody(required = false) Map<String, Object> body) {
        int sessions = 25;
        if (body != null && body.get("sessions") instanceof Number n) {
            sessions = n.intValue();
        }
        return admin.simulate(sessions);
    }

    /** DELETE /api/v1/admin/simulate — wipe every synthetic row; the ledger never keeps the rig's notes. */
    @DeleteMapping("/admin/simulate")
    public Map<String, Object> wipeSimulated() {
        return admin.wipeSimulated();
    }
}
