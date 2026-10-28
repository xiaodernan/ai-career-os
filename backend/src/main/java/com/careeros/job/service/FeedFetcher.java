package com.careeros.job.service;

/**
 * Fetches a feed's body by URL (roadmap 19.2).
 *
 * <p>An interface so the sweep can be tested without a network and so a future connector
 * (19.8) can bring a board-API payload without changing the runner.
 */
public interface FeedFetcher {

    /**
     * The feed's body, or an {@link IllegalStateException} whose message is the reason
     * the pull failed -- short enough for a run row, specific enough to act on.
     */
    String fetch(String url);
}
