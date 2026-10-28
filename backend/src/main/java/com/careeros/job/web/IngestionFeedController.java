package com.careeros.job.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.job.dto.IngestionFeedDtos.FeedItem;
import com.careeros.job.dto.IngestionFeedDtos.FeedPatch;
import com.careeros.job.dto.IngestionFeedDtos.FeedRequest;
import com.careeros.job.dto.IngestionFeedDtos.RunDetail;
import com.careeros.job.dto.IngestionFeedDtos.RunItem;
import com.careeros.job.service.ScheduledIngestionService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * Scheduled ingestion over HTTP (roadmap 19.2). Feeds are the user's subscriptions,
 * runs are what the night did with them; every route is scoped to the caller, so the
 * sweep only ever fetches what its own owner asked for.
 *
 * <p>A run that failed is answered 200 with {@code status: "failed"} and the reason:
 * the feed being down is the outcome the reader asked to see, not an error in their
 * request. Only "this feed is not yours" is a 404.
 */
@RestController
@RequestMapping("/api/v1/ingestion")
public class IngestionFeedController {

    private final ScheduledIngestionService ingestion;

    public IngestionFeedController(ScheduledIngestionService ingestion) {
        this.ingestion = ingestion;
    }

    @GetMapping("/feeds")
    public List<FeedItem> listFeeds(@CurrentUser AuthUser user) {
        return ingestion.listFeeds(user.id());
    }

    @PostMapping("/feeds")
    @ResponseStatus(HttpStatus.CREATED)
    public FeedItem createFeed(@CurrentUser AuthUser user,
                               @RequestBody @Valid FeedRequest request) {
        return ingestion.createFeed(user.id(), request);
    }

    @PatchMapping("/feeds/{id}")
    public FeedItem setEnabled(@CurrentUser AuthUser user, @PathVariable UUID id,
                               @RequestBody @Valid FeedPatch patch) {
        return ingestion.setEnabled(user.id(), id, patch.enabled());
    }

    @DeleteMapping("/feeds/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteFeed(@CurrentUser AuthUser user, @PathVariable UUID id) {
        ingestion.deleteFeed(user.id(), id);
    }

    @PostMapping("/feeds/{id}/run")
    public RunDetail runNow(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return ingestion.runNow(user.id(), id);
    }

    @GetMapping("/runs")
    public List<RunItem> listRuns(@CurrentUser AuthUser user,
                                  @RequestParam(defaultValue = "20") int limit) {
        return ingestion.listRuns(user.id(), limit);
    }

    @GetMapping("/runs/{id}")
    public RunDetail runDetail(@CurrentUser AuthUser user, @PathVariable UUID id) {
        return ingestion.runDetail(user.id(), id);
    }
}
