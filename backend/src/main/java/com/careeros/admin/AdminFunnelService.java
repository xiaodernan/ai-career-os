package com.careeros.admin;

import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * Where the readers fall (Epic 258).
 *
 * <p>The overseer's third question after "how big is this place?" and "is anything
 * arriving?": <em>where do they go?</em> Every stage is a count of <b>distinct readers</b>,
 * never rows, read straight off the tables the product already writes. No reader, no name,
 * no row ever leaves this route; the sharpest thing it can say about anyone is "some number
 * of us stopped here".
 *
 * <p>Two honest properties are load-bearing:
 * <ul>
 *   <li>The funnel line is monotone on this install by construction of what the product is:
 *       you must upload to match, you must apply to practice an interview, you must interview
 *       to hold an offer. Matched is reported <b>beside</b> the line, not inside it, because
 *       readers apply without any match ever landing — most of them, in fact.</li>
 *   <li>The seed corpus means stage counts are a fact of this install's history, not a
 *       conversion prediction. The page says so in so many words.</li>
 * </ul>
 *
 * <p>Fixed literals only — no identifier, no table parameter, never a value a request
 * could reach. Cached with the rest of the overseer's reads (30s TTL, fail-open).
 */
@Service
public class AdminFunnelService {

    private final JdbcTemplate jdbc;
    private final AdminCache cache;

    public AdminFunnelService(JdbcTemplate jdbc, AdminCache cache) {
        this.jdbc = jdbc;
        this.cache = cache;
    }

    /** The funnel payload: stages in installation order, plus the matched side-signal. */
    public Map<String, Object> funnel() {
        return cache.get("funnel").orElseGet(() -> {
            List<Map<String, Object>> stages = List.of(
                    stage("registered", "SELECT count(*) FROM users"),
                    stage("uploaded", "SELECT count(*) FROM (SELECT DISTINCT user_id FROM resumes) AS t"),
                    stage("applied", "SELECT count(*) FROM (SELECT DISTINCT user_id FROM applications) AS t"),
                    stage("interviewed", "SELECT count(*) FROM (SELECT DISTINCT user_id FROM interview_sessions) AS t"),
                    stage("offered", "SELECT count(*) FROM (SELECT DISTINCT user_id FROM offers) AS t"));
            Long matched = jdbc.queryForObject(
                    "SELECT count(*) FROM (SELECT DISTINCT user_id FROM job_matches) AS t", Long.class);
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("stages", stages);
            out.put("matchedReaders", matched == null ? 0L : matched);
            cache.put("funnel", out);
            return out;
        });
    }

    private Map<String, Object> stage(String id, String sql) {
        Long n = jdbc.queryForObject(sql, Long.class);
        Map<String, Object> row = new java.util.LinkedHashMap<>();
        row.put("id", id);
        row.put("readers", n == null ? 0L : n);
        return row;
    }
}
