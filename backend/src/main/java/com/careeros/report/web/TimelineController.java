package com.careeros.report.web;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.report.service.TimelineService;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * One timeline over the whole loop (Epic 81).
 *
 * <p>The events come from rows the caller owns -- applications, notes, contacts,
 * resume versions, matches and interview rehearsals -- and the merge is the
 * ai-service's deterministic fold. Nothing here filters, ranks or reorders; the
 * answer is the engine's own {@code {timeline: [...]}} shape, wrapped in the
 * usual envelope. The page exists because the rows already speak and no screen
 * listens to all of them at once.
 */
@RestController
public class TimelineController {

    private final TimelineService timeline;
    private final AiServiceClient ai;

    public TimelineController(TimelineService timeline, AiServiceClient ai) {
        this.timeline = timeline;
        this.ai = ai;
    }

    /** The reader's own timeline, newest merge first — the order is the engine's, not this route's. */
    @GetMapping("/api/v1/timeline")
    public Map<String, Object> timeline(@CurrentUser AuthUser user) {
        return timeline.timeline(user.id());
    }

    /**
     * Epic 345 — one grounded story over the timeline the reader is already looking
     * at. The browser sends the events it renders; the engine writes one paragraph
     * over their own labels/dates and answers null when nothing grounded survives.
     */
    @PostMapping("/api/v1/timeline/narrative")
    public Map<String, Object> narrative(@CurrentUser AuthUser user,
                                         @RequestBody(required = false) NarrativeRequest request) {
        if (request == null) {
            return Map.of();
        }
        List<Map<String, Object>> events = request.events() == null ? List.of() : request.events();
        Map<String, Object> out = ai.careerNarrative(user.id(), events, request.locale());
        return out == null ? Map.of() : out;
    }

    /** Epic 345 — body of the timeline narrative: the events the page already drew + locale. */
    public record NarrativeRequest(List<Map<String, Object>> events, String locale) {
    }
}
