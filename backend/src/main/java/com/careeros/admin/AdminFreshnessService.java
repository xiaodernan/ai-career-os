package com.careeros.admin;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * The eight "newest row" reads the overseer watches (Epic 254).
 *
 * <p>"Are the rivers flowing?" is the operator's second question after "how big is this
 * place?" — the install can be huge and silent, and only the newest timestamps say
 * which. Counts and instants only; no row, no name, no reader's content.
 *
 * <p>Built from the same tables and columns the stats and trends surfaces already read,
 * hard-coded — never from anything a request parameter could reach — so the SQL below is
 * a closed list, not a template.
 */
@Service
public class AdminFreshnessService {

    /** (flow id, table, clock column) — deliberately closed; no user input reaches the SQL. */
    private static final List<Flow> FLOWS = List.of(
            new Flow("users", "users", "created_at"),
            new Flow("applications", "applications", "created_at"),
            new Flow("interviewSessions", "interview_sessions", "started_at"),
            new Flow("agentRuns", "agent_runs", "started_at"),
            new Flow("aiUsageEvents", "ai_usage_events", "created_at"),
            new Flow("knowledgeSources", "knowledge_sources", "created_at"),
            new Flow("jobMatches", "job_matches", "created_at"),
            new Flow("offers", "offers", "created_at"));

    private final JdbcTemplate jdbc;
    private final AdminCache cache;

    public AdminFreshnessService(JdbcTemplate jdbc, AdminCache cache) {
        this.jdbc = jdbc;
        this.cache = cache;
    }

    /** The freshness strip: one row per river, each carrying the table's newest clock or null. */
    public Map<String, Object> freshness() {
        return cache.get("freshness").orElseGet(() -> {
            List<Map<String, Object>> flows = new java.util.ArrayList<>(FLOWS.size());
            for (Flow flow : FLOWS) {
                flows.add(read(flow));
            }
            Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("flows", flows);
            cache.put("freshness", out);
            return out;
        });
    }

    private Map<String, Object> read(Flow flow) {
        Timestamp newest = jdbc.queryForObject(
                "SELECT max(" + flow.column() + ") FROM " + flow.table(), Timestamp.class);
        Map<String, Object> row = new java.util.LinkedHashMap<>();
        row.put("id", flow.id());
        row.put("table", flow.table());
        row.put("newest", timestampToIso(newest));
        return row;
    }

    static String timestampToIso(Timestamp newest) {
        return newest == null ? null : Instant.ofEpochMilli(newest.getTime()).toString();
    }

    private record Flow(String id, String table, String column) {
    }
}
