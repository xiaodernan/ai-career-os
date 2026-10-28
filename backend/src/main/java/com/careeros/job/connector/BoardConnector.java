package com.careeros.job.connector;

/**
 * A real job board behind the ingestion {@code Connector} protocol (roadmap 19.8).
 *
 * <p>The protocol itself is the engine's — ai-service's {@code features.ingestion.Connector}
 * — and its docstring puts implementations "wherever the network access does". This is
 * that half: a connector knows how a reader's board address (a token, a public board
 * page, or the API URL itself) becomes the one URL the fetcher opens. It shapes nothing:
 * the payload the API answers is mapped by the engine, so the same JSON pasted by hand
 * takes the identical road.
 */
public interface BoardConnector {

    /** The feed label this connector answers for — a feed's {@code source}. */
    String source();

    /**
     * The API URL to fetch for this reader input.
     *
     * @throws IllegalArgumentException with a sentence naming what would work when the
     *         input is not this board's address at all
     */
    String apiUrl(String input);
}
