package com.careeros.admin;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * The quiet cohort (Epic 264).
 *
 * <p>The overseer already knows how big the install is and where the readers fall. This is
 * the third question, the one nobody wants to know about: who ever <em>did</em> anything at
 * all, and when. A signup whose lifetime volume of applications + interviews + conversations
 * + resumes is zero joined the world and left without a trace — the install's own numbers
 * answer it exactly, no model, no guessing.
 *
 * <p>Two honest properties:
 * <ul>
 *   <li>Bucketed by the signup's own ISO week (Monday start, UTC), dense like every other
 *       overseer series — a week with no signups reads as zero, not as missing.</li>
 *   <li>"Active" is the literal disjunction of the four tables that record doing —
 *       application, interview session, conversation, resume. Nothing more is claimed. The
 *       number is the install's fact; it says nothing about a particular reader, only about
 *       the population.</li>
 * </ul>
 *
 * <p>Fixed literals only; cached with the rest of the overseer's reads (30s TTL, fail-open).
 */
@Service
public class AdminCohortService {

    private static final int DEFAULT_WEEKS = 12;
    private static final int MAX_WEEKS = 26;

    private final JdbcTemplate jdbc;
    private final AdminCache cache;

    public AdminCohortService(JdbcTemplate jdbc, AdminCache cache) {
        this.jdbc = jdbc;
        this.cache = cache;
    }

    public Map<String, Object> cohort(int weeks) {
        int span = AdminTrends.clampWeeks(weeks);
        return cache.get("cohort:" + span).orElseGet(() -> {
            LocalDate now = LocalDate.now(ZoneOffset.UTC);
            List<String> weeksList = AdminTrends.weeksList(now, span);
            var start = AdminTrends.windowStart(now, span);
            List<Map<String, Object>> rows = jdbc.queryForList(
                    "SELECT to_char(date_trunc('week', u.created_at AT TIME ZONE 'UTC'), 'YYYY-MM-DD') AS wk,"
                            + " count(*) AS registered,"
                            + " count(*) FILTER (WHERE EXISTS (SELECT 1 FROM applications a WHERE a.user_id = u.id)"
                            + "               OR EXISTS (SELECT 1 FROM interview_sessions i WHERE i.user_id = u.id)"
                            + "               OR EXISTS (SELECT 1 FROM conversations c WHERE c.user_id = u.id)"
                            + "               OR EXISTS (SELECT 1 FROM resumes r WHERE r.user_id = u.id)) AS active"
                            + " FROM users u"
                            + " WHERE u.created_at >= ?"
                            + " GROUP BY 1"
                            + " ORDER BY 1",
                    java.sql.Timestamp.from(start));
            // Fold onto the dense week list so the wire shape matches every other overseer series.
            Map<String, long[]> byWeek = new java.util.HashMap<>();
            for (Map<String, Object> row : rows) {
                Object wk = row.get("wk");
                Number registered = (Number) row.get("registered");
                Number active = (Number) row.get("active");
                if (wk != null && registered != null) {
                    byWeek.put(wk.toString(), new long[] { registered.longValue(), active == null ? 0L : active.longValue() });
                }
            }
            List<Map<String, Object>> cohort = new java.util.ArrayList<>(weeksList.size());
            for (String week : weeksList) {
                long[] pair = byWeek.getOrDefault(week, new long[] { 0L, 0L });
                Map<String, Object> row = new java.util.LinkedHashMap<>();
                row.put("week", week);
                row.put("registered", pair[0]);
                row.put("active", pair[1]);
                cohort.add(row);
            }
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("weeks", weeksList);
            out.put("weeksRequested", span);
            out.put("cohort", cohort);
            cache.put("cohort:" + span, out);
            return out;
        });
    }
}
