package com.careeros.knowledge.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * The stuck-upload repair clock as a scrape sees it (Epic 418).
 *
 * <p>Two readings, and each answers a different question than the other can. The counter says
 * what happened to the documents a tick looked at, with the outcome as a tag rather than in the
 * name, so "how many of the offers were refused" is one division and a new outcome is a tag
 * value instead of a new metric. The gauge says whether the clock is running at all: a tick
 * that found nothing still moves it, which is the only way an empty board can be told apart
 * from a stopped scheduler — the reading this install's other clocks settled on for exactly that
 * reason (the reminder tick, the retention sweep).
 *
 * <p>All four outcome series are registered at boot, not on first use. The outcomes are a closed
 * vocabulary the code can prove, and a rate() over a tag that has never been seen returns
 * nothing rather than zero: a repair clock that has never been refused would look healthier on
 * the dashboard than one that is refusing, which is backwards.
 *
 * <p>The gauge starts at this process's own boot time rather than at zero, as
 * {@link com.careeros.job.service.IngestionMetrics} does: zero is an epoch second in 1970, so a
 * fresh deploy would page before its first tick had a chance to run.
 */
@Component
public class IngestionRepairMetrics {

    /** Micrometer names; the Prometheus exporter renders the dots as underscores. */
    static final String REPAIRS = "careeros.ingestion.repairs";
    static final String LAST_TICK = "careeros.ingestion.repair.last.tick.timestamp";

    /** The document was handed back to the engine. */
    static final String REQUEUED = "requeued";
    /** The engine refused the offer; the row keeps its state and the next tick tries again. */
    static final String REFUSED = "refused";
    /** Another replica claimed the row first, so this tick has nothing to do with it. */
    static final String CONTENDED = "contended";
    /** The offer limit is spent: the document is failed, with its reason, rather than retried. */
    static final String EXHAUSTED = "exhausted";

    private static final String REPAIRS_DESCRIPTION =
            "Documents the stuck-ingestion repair clock looked at, by what happened to them";

    private final MeterRegistry registry;
    private final AtomicLong lastTick;

    public IngestionRepairMetrics(MeterRegistry registry) {
        this.registry = registry;
        for (String outcome : new String[] {REQUEUED, REFUSED, CONTENDED, EXHAUSTED}) {
            Counter.builder(REPAIRS)
                    .tag("outcome", outcome)
                    .description(REPAIRS_DESCRIPTION)
                    .register(registry);
        }
        this.lastTick = new AtomicLong(Instant.now().getEpochSecond());
        Gauge.builder(LAST_TICK, lastTick, AtomicLong::doubleValue)
                .description("Epoch seconds of the last repair-clock tick that finished, empty or not")
                .register(registry);
    }

    /** One document this tick was allowed to look at, ending in exactly one of the four ways. */
    void record(String outcome) {
        registry.counter(REPAIRS, "outcome", outcome).increment();
    }

    /**
     * The clock ran. Moved whether or not anything was stuck, because the reading exists to
     * answer "is this clock alive", and a tick that found an empty board is a live clock.
     */
    void tickFinished() {
        lastTick.set(Instant.now().getEpochSecond());
    }
}
