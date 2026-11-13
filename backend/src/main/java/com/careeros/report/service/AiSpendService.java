package com.careeros.report.service;

import com.careeros.activity.repository.AiUsageEventRepository;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Today's AI spend, from the one ledger the model calls already write.
 *
 * <p>The health report (16.1) answers "is the agent healthy"; this answers "what did
 * today cost me" without asking a model — every row in `ai_usage_events` is a bill
 * the engine already booked. UTC day, like the nightly reports: one clock, one answer.
 *
 * <p>The cap is a *gauge*, not a gate. `careeros.ai.daily-spend-cap-usd` (env
 * `CAREEROS_DAILY_SPEND_CAP_USD`) anchors the progress bar the dashboard renders;
 * nothing is refused or throttled here — enforcement belongs to the engine's own
 * deadline backstop, not to a dashboard read. A cap of `0` removes the bar.
 */
@Service
public class AiSpendService {

    private final AiUsageEventRepository usage;

    @Value("${careeros.ai.daily-spend-cap-usd:10.00}")
    private BigDecimal capUsd;

    public AiSpendService(AiUsageEventRepository usage) {
        this.usage = usage;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> today(UUID userId) {
        OffsetDateTime dayStart = LocalDate.now(ZoneOffset.UTC)
                .atStartOfDay()
                .atOffset(ZoneOffset.UTC);

        var rows = usage.usageTotalsSince(userId, dayStart);
        Object[] row = rows == null || rows.isEmpty() ? null : rows.get(0);
        int index = 0;
        BigDecimal cost = bigDecimalAt(row, index++, BigDecimal.ZERO);
        long in = longAt(row, index++);
        long out = longAt(row, index++);
        long cached = longAt(row, index++);
        long calls = longAt(row, index);

        double cacheHitRatio = in > 0 ? (double) cached / (double) in : 0.0;
        boolean capEnabled = capUsd != null && capUsd.signum() > 0;
        boolean capExceeded = capEnabled && cost.compareTo(capUsd) >= 0;

        // The Map stays the exact shape the wire carries; the contract census reads
        // the puts in this method, so a key added anywhere else would go unbound.
        Map<String, Object> out_ = new LinkedHashMap<>();
        out_.put("dayStart", dayStart.toString());
        out_.put("costUsd", cost);
        out_.put("inputTokens", in);
        out_.put("outputTokens", out);
        out_.put("cachedTokens", cached);
        out_.put("calls", calls);
        out_.put("cacheHitRatio", Math.round(cacheHitRatio * 10000.0) / 10000.0);
        out_.put("capUsd", capEnabled ? capUsd : BigDecimal.ZERO);
        out_.put("capEnabled", capEnabled);
        out_.put("capExceeded", capExceeded);
        return out_;
    }

    private static BigDecimal bigDecimalAt(Object[] row, int i, BigDecimal fallback) {
        if (row == null || row.length <= i || row[i] == null) {
            return fallback;
        }
        return row[i] instanceof BigDecimal bd ? bd : new BigDecimal(row[i].toString());
    }

    private static long longAt(Object[] row, int i) {
        if (row == null || row.length <= i || row[i] == null) {
            return 0L;
        }
        return ((Number) row[i]).longValue();
    }
}
