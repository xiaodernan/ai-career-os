package com.careeros.attention.service;

import com.careeros.attention.entity.AttentionEvent;
import com.careeros.attention.repository.AttentionRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * The admin view over the attention rows (Epic 267).
 *
 * <p>Twenty numbers, one question per side: how are readers behaving, and is this a page
 * worth keeping. Counts and averages only — never a per-reader row. Inputs arrive the
 * way the browser sends them (path + event + optional value), stored and counted.
 */
@Service
public class AttentionAdminService {

    private static final int DEFAULT_DAYS = 30;
    /** Hard cap per simulate call — every call must stay a seed, not a flood. */
    static final int MAX_SESSIONS = 200;

    private final JdbcTemplate jdbc;
    private final AttentionRepository repo;

    public AttentionAdminService(JdbcTemplate jdbc, AttentionRepository repo) {
        this.jdbc = jdbc;
        this.repo = repo;
    }

    public Map<String, Object> summary() {
        int days = DEFAULT_DAYS;
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("days", days);
        out.put("landings", one("SELECT count(*) FROM attention_events WHERE event='land' AND created_at >= now() - interval '" + days + " days'"));
        out.put("dwells",   one("SELECT count(*) FROM attention_events WHERE event='dwell' AND created_at >= now() - interval '" + days + " days'"));
        out.put("acts",     one("SELECT count(*) FROM attention_events WHERE event='act' AND created_at >= now() - interval '" + days + " days'"));
        // The two behaviours the operator explicitly asked to observe: a reader who leaves
        // almost as soon as they land, and one who clicks around without settling. Both are
        // first-class events now, counted straight off the rows — never inferred from a dwell.
        out.put("bounces", one("SELECT count(*) FROM attention_events WHERE event='bounce' AND created_at >= now() - interval '" + days + " days'"));
        long landings = (long) out.get("landings");
        long bounces = (long) out.get("bounces");
        out.put("bounceRatePct", landings == 0L ? 0.0
                : Math.round((10000.0 * bounces / landings)) / 100.0);
        out.put("aimless", one("SELECT count(*) FROM attention_events WHERE event='aimless' AND created_at >= now() - interval '" + days + " days'"));
        out.put("signedLandings",    one("SELECT count(*) FROM attention_events WHERE event='land' AND user_id IS NOT NULL AND created_at >= now() - interval '" + days + " days'"));
        out.put("anonymousLandings", one("SELECT count(*) FROM attention_events WHERE event='land' AND user_id IS NULL AND created_at >= now() - interval '" + days + " days'"));

        long dwellMs = 0L;
        Long avg = jdbc.queryForObject(
            "SELECT coalesce(avg((value)::bigint), 0) FROM attention_events WHERE event='dwell' AND value ~ '^[0-9]+$'"
                + " AND created_at >= now() - interval '" + days + " days'",
            Long.class);
        dwellMs = avg == null ? 0L : avg;
        out.put("dwellPerLandingMs", dwellMs);

        List<Map<String, Object>> topLandings = jdbc.queryForList(
            "SELECT path, count(*) FILTER (WHERE event='land') AS landings,"
                    + " count(*) FILTER (WHERE event='dwell') AS dwells,"
                    + " count(*) FILTER (WHERE event='act') AS acts,"
                    + " count(*) FILTER (WHERE event='bounce') AS bounces,"
                    + " count(*) FILTER (WHERE event='aimless') AS aimless"
                    + " FROM attention_events"
                    + " WHERE created_at >= now() - interval '" + days + " days'"
                    + "   AND path NOT LIKE '/admin%'"
                    + " GROUP BY path ORDER BY landings DESC LIMIT 12");
        out.put("topLandings", topLandings);
        return out;
    }

    private long one(String sql) {
        Long n = jdbc.queryForObject(sql, Long.class);
        return n == null ? 0L : n;
    }

    /* ------------------------- the simulator (Epic 289) ------------------------- */

    /**
     * Paths a stranger actually opens on this install's front, with the weight of
     * that attention. The distribution is the install's own (public surfaces by far
     * outweigh the pantry), not a uniform sample.
     */
    private static final String[] SIM_PATHS = {"/", "/jobs", "/tour", "/playbook", "/resumes",
            "/growth", "/letters", "/interviews", "/applications"};
    private static final int[] SIM_WEIGHTS = {30, 22, 12, 10, 8, 6, 5, 4, 3};

    /** Session flavors: 25% bounce, 12% click around lost, 38% browse, 25% settle in. */
    private static final int BOUNCE = 25;
    private static final int AIMLESS_UNTIL = 37;
    private static final int BROWSER_UNTIL = 75;

    /**
     * One call seeds a quiet week of synthetic visitors. Every row carries the
     * journey marker `synthetic` so the install's own ledger can never mistake them
     * for readers. Deterministic per seed — each call draws a fresh seed, so repeats
     * are varied yet bounded (≤200 sessions).
     */
    public Map<String, Object> simulate(int sessions) {
        int n = Math.max(1, Math.min(MAX_SESSIONS, sessions));
        Random random = new Random(System.nanoTime() ^ 0x5deece66dL);
        List<AttentionEvent> rows = simulateRows(n, random);
        repo.saveAll(rows);
        return Map.of("recorded", rows.size(), "journey", "synthetic", "sessions", n);
    }

    /**
     * The rows one simulate call creates — extracted for the honesty gate. Bench
     * identity: every row carries userId null and journey "synthetic", across flavors.
     */
    static List<AttentionEvent> simulateRows(int sessions, Random random) {
        int n = Math.max(1, Math.min(MAX_SESSIONS, sessions));
        List<AttentionEvent> rows = new ArrayList<>();
        for (int i = 0; i < n; i += 1) {
            String path = pickPath(random);
            rows.add(new AttentionEvent(null, "synthetic", path, "land", null));
            int roll = random.nextInt(100);
            if (roll < BOUNCE) {
                // Impatient bounce: land then leave almost immediately. The close is now a
                // first-class event carrying the time-on-page, not a guess from a short dwell.
                rows.add(bounceRow(random, path));
                continue;
            }
            if (roll < AIMLESS_UNTIL) {
                // Disorientation: a random walk with back-and-forth hops and no settled read.
                // Each hop is an `aimless` row so the overseer can see a lost reader, not just
                // another landing. A→B→A repeats are the signature the user described.
                rows.add(dwellRow(random, path, 400, 2_000));
                String first = pickPath(random);
                rows.add(new AttentionEvent(null, "synthetic", first, "aimless", null));
                String back = path;
                rows.add(new AttentionEvent(null, "synthetic", back, "aimless", null));
                int hops = 1 + random.nextInt(3);
                for (int j = 0; j < hops; j += 1) {
                    rows.add(new AttentionEvent(null, "synthetic", pickPath(random), "aimless", null));
                }
                continue;
            }
            if (roll < BROWSER_UNTIL) {
                rows.add(dwellRow(random, path, 15_000, 90_000));
                int extras = 1 + random.nextInt(2); // one or two other pages
                for (int j = 0; j < extras; j += 1) {
                    String other = pickPath(random);
                    rows.add(new AttentionEvent(null, "synthetic", other, "land", null));
                    if (random.nextDouble() < 0.7) {
                        rows.add(dwellRow(random, other, 10_000, 60_000));
                    }
                }
                if (random.nextDouble() < 0.6) {
                    rows.add(new AttentionEvent(null, "synthetic", path, "act", null));
                }
                continue;
            }
            // engaged: three to five dwell reads, two to four acts
            rows.add(dwellRow(random, path, 60_000, 420_000));
            int dwells = 2 + random.nextInt(3);
            for (int j = 0; j < dwells; j += 1) {
                rows.add(dwellRow(random, pickPath(random), 45_000, 300_000));
            }
            int acts = 2 + random.nextInt(3);
            for (int j = 0; j < acts; j += 1) {
                rows.add(new AttentionEvent(null, "synthetic", path, "act", null));
            }
        }
        return rows;
    }

    private static AttentionEvent dwellRow(Random random, String path, long minMs, long maxMs) {
        long span = Math.max(1, maxMs - minMs);
        long dwell = minMs + Math.abs(random.nextLong() % (span + 1));
        return new AttentionEvent(null, "synthetic", path, "dwell", String.valueOf(dwell));
    }

    /** An impatient leave: the bounce row carries how long the reader was actually there. */
    private static AttentionEvent bounceRow(Random random, String path) {
        long ms = 300 + Math.abs(random.nextLong() % 4_000); // 0.3–4.3s: left as soon as they landed
        return new AttentionEvent(null, "synthetic", path, "bounce", String.valueOf(ms));
    }

    private static String pickPath(Random random) {
        int roll = random.nextInt(100);
        int cumulative = 0;
        for (int i = 0; i < SIM_WEIGHTS.length; i += 1) {
            cumulative += SIM_WEIGHTS[i];
            if (roll < cumulative) {
                return SIM_PATHS[i];
            }
        }
        return SIM_PATHS[0];
    }

    /** Delete every synthetic row; the door never touches anonymous-real rows. */
    @org.springframework.transaction.annotation.Transactional
    public Map<String, Object> wipeSimulated() {
        long deleted = repo.deleteByJourney("synthetic");
        return Map.of("wiped", deleted, "journey", "synthetic");
    }
}
