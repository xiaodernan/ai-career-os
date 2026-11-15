package com.careeros.admin;

import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * The install's own tally, straight off the tables (Epic 248).
 *
 * <p>Every figure here is a count of rows the working system itself wrote — no fixture, no
 * estimate, no preview of the next quarter. A number with a border, not a bet.
 *
 * <p>Public by design: no identifier, no name, no content from any row reaches this route.
 * What it answers is "how big is this place" — counts only, nothing per user. The passphrase
 * check lives in the frontend because this install has exactly one operator; the backstop for
 * a bigger world would be an auth wall in front, not a header check here.
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminStatsController {

    private final JdbcTemplate jdbc;

    public AdminStatsController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/stats")
    public Map<String, Object> stats() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("users", count("users"));
        out.put("resumes", count("resumes"));
        out.put("applications", count("applications"));
        out.put("interviewsPracticed", count("interview_sessions"));
        out.put("interviewTurns", count("interview_turns"));
        out.put("agentRuns", count("agent_runs"));
        out.put("agentTraces", count("agent_traces"));
        out.put("aiUsageEvents", count("ai_usage_events"));
        out.put("knowledgeSources", count("knowledge_sources"));
        out.put("notesKept", count("user_notes"));
        out.put("coverLetters", count("application_letters"));
        out.put("contacts", count("contacts"));
        out.put("memories", count("user_memories"));
        out.put("companies", count("companies"));
        out.put("jobs", count("jobs"));
        out.put("matches", count("job_matches"));
        out.put("conversations", count("conversations"));
        out.put("messages", count("messages"));
        out.put("savedSearches", count("saved_searches"));
        out.put("offers", count("offers"));
        return out;
    }

    private long count(String table) {
        Long n = jdbc.queryForObject("select count(*) from " + table, Long.class);
        return n == null ? 0L : n;
    }
}
