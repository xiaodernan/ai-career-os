package com.careeros.job.service;

import com.careeros.job.entity.SavedSearch;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedSearchRepository;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The question a saved search keeps, asked again (roadmap 29.1).
 *
 * <p>A saved search was a named criterion set with no voice: the board answered it on the
 * click that applied it, and a posting that arrived afterwards went unmentioned. This service
 * is the missing half. It hands the stored criteria to the board's own search -- the same
 * predicate the list screen runs, so an alert cannot match a set the board would not answer --
 * and asks only how many postings appeared since a moment and when the newest one did.
 *
 * <p>"Since" is the later of the search's own creation and a seven-day floor, the same
 * lookback the inbox uses for pulls: a search kept six months ago should not announce the
 * hundred postings that were already on the board when it was saved, and a signal ten days
 * unread is history, not news. Both ends are read off clocks the row already carries, so
 * nothing has to be stored to remember what the reader was told.
 *
 * <p>An empty criterion set is skipped rather than answered: it would match the whole board,
 * and an alert about everything is an alert about nothing. The create route refuses one, so
 * this is the read-side half of the same rule for a row that predates it.
 */
@Service
public class SavedSearchMatcher {

    /** How far back a posting is still news; the inbox's own pull window, rounded to days. */
    static final int NEW_WINDOW_DAYS = 7;

    /** One search with news. The episode (the newest arrival) is the caller's to key. */
    public record Alert(UUID searchId, String name, int count, OffsetDateTime newestAt,
                        String link) {
    }

    private final SavedSearchRepository searches;
    private final JobSearchRepository board;

    public SavedSearchMatcher(SavedSearchRepository searches, JobSearchRepository board) {
        this.searches = searches;
        this.board = board;
    }

    @Transactional(readOnly = true)
    public List<Alert> alerts(UUID userId, OffsetDateTime now) {
        List<Alert> out = new ArrayList<>();
        for (SavedSearch saved : searches.findByUserIdOrderByCreatedAtDesc(userId)) {
            Map<String, Object> criteria = saved.getCriteria();
            if (criteria == null || criteria.isEmpty()) {
                continue;
            }
            JobSearchRepository.MatchStats stats =
                    board.matchStats(filters(userId, criteria), windowStart(saved, now));
            if (stats.count() <= 0 || stats.newest() == null) {
                continue;
            }
            out.add(new Alert(saved.getId(), saved.getName(),
                    (int) Math.min(Integer.MAX_VALUE, stats.count()), stats.newest(),
                    link(criteria)));
        }
        return out;
    }

    /**
     * The stored criteria in the board's own filter shape. The canonical map (19.1) already
     * uses the board's names, so this is a translation of types, not of vocabulary: JSON
     * numbers arrive as any {@link Number}, skills as a JSON array, and the stored
     * {@code remote=true} becomes the {@code remote_type} value the board's SQL compares.
     * Closed postings are not news -- an alert that a role someone can no longer apply to
     * exists is noise.
     */
    private static JobSearchRepository.Filters filters(UUID userId, Map<String, Object> criteria) {
        return new JobSearchRepository.Filters(userId,
                text(criteria.get("q")),
                skills(criteria.get("skills")),
                text(criteria.get("location")),
                Boolean.TRUE.equals(criteria.get("remote")) ? "remote" : null,
                text(criteria.get("company")),
                number(criteria.get("minSalary")),
                number(criteria.get("maxSalary")),
                "open", "posted", 0, 1, null);
    }

    private static OffsetDateTime windowStart(SavedSearch saved, OffsetDateTime now) {
        OffsetDateTime floor = now.minusDays(NEW_WINDOW_DAYS);
        OffsetDateTime created = saved.getCreatedAt();
        return created == null || created.isBefore(floor) ? floor : created;
    }

    /**
     * The board's URL for the same question, in the page's own spellings, so the mail's link
     * lands on the filtered list rather than on an empty board with the criteria somewhere
     * else. Values are encoded; the page decodes them with {@code URLSearchParams}.
     */
    private static String link(Map<String, Object> criteria) {
        StringBuilder query = new StringBuilder();
        append(query, "q", text(criteria.get("q")));
        List<String> skills = skills(criteria.get("skills"));
        append(query, "skills", skills.isEmpty() ? null : String.join(",", skills));
        append(query, "location", text(criteria.get("location")));
        append(query, "company", text(criteria.get("company")));
        if (Boolean.TRUE.equals(criteria.get("remote"))) {
            append(query, "remote", "1");
        }
        Integer min = number(criteria.get("minSalary"));
        Integer max = number(criteria.get("maxSalary"));
        append(query, "min_salary", min == null ? null : min.toString());
        append(query, "max_salary", max == null ? null : max.toString());
        return query.isEmpty() ? "/jobs" : "/jobs?" + query;
    }

    /** One query-string pair, encoded; the boolean's {@code 1} is the page's own spelling. */
    private static void append(StringBuilder query, String key, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        if (!query.isEmpty()) {
            query.append('&');
        }
        query.append(key).append('=')
                .append(URLEncoder.encode(value, StandardCharsets.UTF_8));
    }

    private static String text(Object value) {
        if (value == null) {
            return null;
        }
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }

    /** A stored skills array as strings; a scalar that predates the array is still one skill. */
    private static List<String> skills(Object value) {
        if (value instanceof List<?> list) {
            return list.stream().map(SavedSearchMatcher::text)
                    .filter(skill -> skill != null).toList();
        }
        String single = text(value);
        return single == null ? List.of() : List.of(single);
    }

    private static Integer number(Object value) {
        return value instanceof Number number ? number.intValue() : null;
    }
}
