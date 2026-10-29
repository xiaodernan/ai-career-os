package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.job.entity.SavedSearch;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedSearchRepository;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * A saved search's second life (roadmap 29.1): the named question asked again against the
 * board's own search, with a window that starts at the later of the search's creation and the
 * news horizon.
 *
 * <p>What is pinned: the stored canonical criteria reach the board as the board's own filter
 * types (JSON numbers, a skills array, {@code remote=true} as the {@code remote_type} value,
 * open postings only); "since" is the search's creation while that is still news and the
 * seven-day floor once it is not; a question with no new answers raises nothing; and the link
 * lands on the board's own URL spelling so the reader sees the postings, not an empty page.
 */
class SavedSearchMatcherTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID SEARCH = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final OffsetDateTime NOW = OffsetDateTime.parse("2026-10-29T04:47:00Z");

    private SavedSearchRepository searches;
    private JobSearchRepository board;
    private SavedSearchMatcher matcher;

    @BeforeEach
    void setUp() {
        searches = mock(SavedSearchRepository.class);
        board = mock(JobSearchRepository.class);
        matcher = new SavedSearchMatcher(searches, board);
    }

    private static SavedSearch saved(String name, Map<String, Object> criteria,
                                     OffsetDateTime createdAt) {
        SavedSearch row = mock(SavedSearch.class);
        when(row.getId()).thenReturn(SEARCH);
        when(row.getName()).thenReturn(name);
        when(row.getCriteria()).thenReturn(criteria);
        when(row.getCreatedAt()).thenReturn(createdAt);
        return row;
    }

    private void withSearches(SavedSearch... rows) {
        when(searches.findByUserIdOrderByCreatedAtDesc(ALICE)).thenReturn(List.of(rows));
    }

    private JobSearchRepository.Filters asked(OffsetDateTime expectedSince) {
        ArgumentCaptor<JobSearchRepository.Filters> filters =
                ArgumentCaptor.forClass(JobSearchRepository.Filters.class);
        ArgumentCaptor<OffsetDateTime> since = ArgumentCaptor.forClass(OffsetDateTime.class);
        verify(board).matchStats(filters.capture(), since.capture());
        assertThat(since.getValue()).isEqualTo(expectedSince);
        return filters.getValue();
    }

    @Test
    void the_stored_criteria_become_the_boards_own_filters() {
        Map<String, Object> criteria = new LinkedHashMap<>();
        criteria.put("q", "backend engineer");
        criteria.put("skills", List.of("Java", "C++"));
        criteria.put("location", "Berlin");
        criteria.put("company", "Acme");
        criteria.put("remote", true);
        criteria.put("minSalary", 120000);
        criteria.put("maxSalary", 180000);
        OffsetDateTime created = NOW.minusDays(2);
        withSearches(saved("Backend roles", criteria, created));
        when(board.matchStats(any(), any()))
                .thenReturn(new JobSearchRepository.MatchStats(0, null));

        matcher.alerts(ALICE, NOW);

        JobSearchRepository.Filters filters = asked(created);
        assertThat(filters.userId()).isEqualTo(ALICE);
        assertThat(filters.q()).isEqualTo("backend engineer");
        assertThat(filters.skills()).containsExactly("Java", "C++");
        assertThat(filters.location()).isEqualTo("Berlin");
        assertThat(filters.company()).isEqualTo("Acme");
        assertThat(filters.remote()).isEqualTo("remote");
        assertThat(filters.minSalary()).isEqualTo(120000);
        assertThat(filters.maxSalary()).isEqualTo(180000);
        assertThat(filters.status()).isEqualTo("open");
        assertThat(filters.companyId()).isNull();
        assertThat(filters.embedding()).isNull();
    }

    @Test
    void a_search_older_than_the_news_window_asks_only_for_the_lookback() {
        withSearches(saved("Old question", Map.of("q", "rust"),
                NOW.minusDays(SavedSearchMatcher.NEW_WINDOW_DAYS + 20)));
        when(board.matchStats(any(), any()))
                .thenReturn(new JobSearchRepository.MatchStats(0, null));

        matcher.alerts(ALICE, NOW);

        asked(NOW.minusDays(SavedSearchMatcher.NEW_WINDOW_DAYS));
    }

    @Test
    void a_search_the_board_has_no_news_for_raises_nothing() {
        withSearches(saved("Quiet question", Map.of("q", "cobol"), NOW.minusDays(1)));
        when(board.matchStats(any(), any()))
                .thenReturn(new JobSearchRepository.MatchStats(0, null));

        assertThat(matcher.alerts(ALICE, NOW)).isEmpty();
    }

    @Test
    void an_empty_criterion_set_is_not_a_question_about_the_whole_board() {
        withSearches(saved("Everything", Map.of(), NOW.minusDays(1)));

        assertThat(matcher.alerts(ALICE, NOW)).isEmpty();
        verify(board, never()).matchStats(any(), any());
    }

    @Test
    void the_alert_carries_the_name_count_newest_arrival_and_the_boards_own_url() {
        Map<String, Object> criteria = new LinkedHashMap<>();
        criteria.put("q", "backend engineer");
        criteria.put("skills", List.of("Java", "C++"));
        criteria.put("location", "Berlin");
        criteria.put("remote", true);
        criteria.put("minSalary", 120000);
        OffsetDateTime newest = NOW.minusHours(3);
        withSearches(saved("Backend roles", criteria, NOW.minusDays(30)));
        when(board.matchStats(any(), any()))
                .thenReturn(new JobSearchRepository.MatchStats(6, newest));

        List<SavedSearchMatcher.Alert> alerts = matcher.alerts(ALICE, NOW);

        assertThat(alerts).containsExactly(new SavedSearchMatcher.Alert(
                SEARCH, "Backend roles", 6, newest,
                "/jobs?q=backend+engineer&skills=Java%2CC%2B%2B&location=Berlin&remote=1"
                        + "&min_salary=120000"));
    }
}
