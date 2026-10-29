package com.careeros.auth.retention;

import com.careeros.auth.repository.EmailChangeTokenRepository;
import com.careeros.auth.repository.PasswordResetTokenRepository;
import com.careeros.auth.repository.RefreshTokenRepository;
import com.careeros.config.AppProperties;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Deletes credential rows that have been expired for longer than the grace window (roadmap
 * 28.1).
 *
 * <p>A token row outlives the token. Nothing reads an expired refresh, reset or address-change
 * token -- every lookup is by hash and every consumer checks expiry -- but the row stays until
 * someone deletes it, and each sign-in, reset request and address move writes one. Left alone,
 * the three credential tables grow with the install's entire history of them.
 *
 * <p>The cutoff is the sweep's clock minus a grace window, not "expired now": a row is deleted
 * only once its expiry is that far behind the clock, so a clock-skewed client, a support
 * investigation or a late-arriving request still finds its row. The default is thirty days past
 * expiry, and the window is an operator knob ({@code app.retention.expired-token-days}).
 *
 * <p>Each table is swept in its own transaction, so a lock timeout on one leaves the other two
 * pruned rather than rolling the whole night back; a failed table is logged and omitted from
 * the summary, and no metric moves for it, so the counter tells an operator which tables were
 * actually swept. The pass then moves the heartbeat gauge even if a table failed: the gauge
 * answers whether the schedule still runs, and a pass that ran and failed is a different fault
 * from a clock that stopped. The tables that hold visible history -- AI usage events behind the
 * activity totals, notification read state, ingestion runs, weekly letters -- are deliberately
 * absent: removing their rows would rewrite a screen or re-announce a story the reader already
 * settled.
 */
@Component
public class RetentionSweeper {

    static final String REFRESH_TOKENS = "refresh_tokens";
    static final String PASSWORD_RESET_TOKENS = "password_reset_tokens";
    static final String EMAIL_CHANGE_TOKENS = "email_change_tokens";

    private static final Logger log = LoggerFactory.getLogger(RetentionSweeper.class);

    private final RefreshTokenRepository refreshTokens;
    private final PasswordResetTokenRepository resetTokens;
    private final EmailChangeTokenRepository emailChangeTokens;
    private final AppProperties props;
    private final RetentionMetrics metrics;

    public RetentionSweeper(RefreshTokenRepository refreshTokens,
                            PasswordResetTokenRepository resetTokens,
                            EmailChangeTokenRepository emailChangeTokens,
                            AppProperties props, RetentionMetrics metrics) {
        this.refreshTokens = refreshTokens;
        this.resetTokens = resetTokens;
        this.emailChangeTokens = emailChangeTokens;
        this.props = props;
        this.metrics = metrics;
    }

    @Scheduled(cron = "${careeros.retention.cron:0 47 4 * * *}")
    public void nightly() {
        sweep(OffsetDateTime.now());
    }

    /**
     * One sweep at {@code now}. Package-private so the tests can hand it a fixed clock instead
     * of waiting for 04:47.
     */
    Sweep sweep(OffsetDateTime now) {
        int days = Math.max(0, props.getRetention().getExpiredTokenDays());
        OffsetDateTime cutoff = now.minusDays(days);
        Map<String, Integer> deleted = new LinkedHashMap<>();
        List<String> failed = new ArrayList<>();
        for (String table : List.of(REFRESH_TOKENS, PASSWORD_RESET_TOKENS, EMAIL_CHANGE_TOKENS)) {
            try {
                int rows = switch (table) {
                    case REFRESH_TOKENS -> refreshTokens.deleteExpiredBefore(cutoff);
                    case PASSWORD_RESET_TOKENS -> resetTokens.deleteExpiredBefore(cutoff);
                    default -> emailChangeTokens.deleteExpiredBefore(cutoff);
                };
                deleted.put(table, rows);
                metrics.record(table, rows);
            } catch (RuntimeException e) {
                failed.add(table);
                log.warn("Retention sweep failed for {}; the other tables keep their own rows", table, e);
            }
        }
        metrics.recordSweep(now);
        log.info("Retention sweep removed {} expired credential row(s) older than {} ({})",
                deleted.values().stream().mapToInt(Integer::intValue).sum(), cutoff, deleted);
        return new Sweep(deleted, failed);
    }

    /** What one sweep removed per table, and the tables it could not finish. */
    record Sweep(Map<String, Integer> deleted, List<String> failed) {
    }
}
