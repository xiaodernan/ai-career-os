package com.careeros.gateway;

import reactor.core.publisher.Mono;

/**
 * One rate-limit decision, however it is stored.
 *
 * <p>The interface exists so the edge can hold two answers at once: a budget that lives
 * in this process and a budget that lives in Redis. The filter picks one, and the
 * interesting behaviour -- falling back when the shared one is unreachable -- is a
 * composition of the two rather than a branch buried in a filter.
 */
public interface EdgeBudget {

    /** {@code true} when the caller may spend a token now. Never throws; errors are signals. */
    Mono<Boolean> take(String identity);

    /** Where the decision was made, for logs and for the metric that counts fallbacks. */
    String name();
}
