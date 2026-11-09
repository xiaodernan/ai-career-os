package com.careeros.report.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.report.service.TimelineService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
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

    public TimelineController(TimelineService timeline) {
        this.timeline = timeline;
    }

    /** The reader's own timeline, newest merge first — the order is the engine's, not this route's. */
    @GetMapping("/api/v1/timeline")
    public Map<String, Object> timeline(@CurrentUser AuthUser user) {
        return timeline.timeline(user.id());
    }
}
