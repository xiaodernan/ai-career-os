package com.careeros.job.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.job.entity.SavedSearch;
import com.careeros.job.repository.SavedSearchRepository;
import com.careeros.job.service.SavedSearchService;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The saved-search routes (roadmap 19.1).
 *
 * <p>Two claims are worth a route-level test. The first is ownership: every
 * query is anchored on the caller's id, so a saved search is one user's
 * question and never another's to read or delete. The second is that the
 * stored criteria are the board's own vocabulary — a route that accepted
 * `remote: false` as a stored filter, or a blank location, would hand the
 * alert matcher a criterion the board has never promised to answer.
 */
class SavedSearchControllerTest {

    private static final UUID ALICE = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID SAVED = UUID.fromString("33333333-3333-4333-8333-333333333333");

    private SavedSearchRepository repository;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        repository = mock(SavedSearchRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(
                        new SavedSearchController(new SavedSearchService(repository)))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(ALICE, "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @SuppressWarnings("unchecked")
    private SavedSearch storedRow() {
        ArgumentCaptor<SavedSearch> cap = ArgumentCaptor.forClass(SavedSearch.class);
        verify(repository).save(cap.capture());
        return cap.getValue();
    }

    @Test
    void a_saved_search_is_written_under_the_caller_with_the_boards_own_names() throws Exception {
        when(repository.save(any(SavedSearch.class))).thenAnswer(i -> i.getArgument(0));

        mvc.perform(post("/api/v1/saved-searches")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"name":"Remote backend",
                                 "criteria":{"q":" backend ","location":" ",
                                             "remote":false,"minSalary":30000,
                                             "skills":["Java"]}}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.name").value("Remote backend"))
                .andExpect(jsonPath("$.data.criteria.q").value("backend"))
                .andExpect(jsonPath("$.data.criteria.minSalary").value(30000));

        SavedSearch row = storedRow();
        assertThat(row.getUserId()).isEqualTo(ALICE);
        assertThat(row.getCriteria()).containsEntry("q", "backend")
                .containsEntry("minSalary", 30000)
                .doesNotContainKeys("remote", "location");
    }

    @Test
    void the_list_is_the_callers_own_and_newest_first() throws Exception {
        SavedSearch first = new SavedSearch();
        first.setUserId(ALICE);
        first.setName("First");
        first.setCriteria(java.util.Map.of("q", "backend"));
        SavedSearch second = new SavedSearch();
        second.setUserId(ALICE);
        second.setName("Second");
        second.setCriteria(java.util.Map.of("location", "Hangzhou"));
        when(repository.findByUserIdOrderByCreatedAtDesc(ALICE)).thenReturn(List.of(first, second));

        mvc.perform(get("/api/v1/saved-searches"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].name").value("First"))
                .andExpect(jsonPath("$.data[1].criteria.location").value("Hangzhou"));

        verify(repository).findByUserIdOrderByCreatedAtDesc(ALICE);
    }

    @Test
    void deleting_another_users_search_is_a_404_naming_the_code() throws Exception {
        when(repository.findByIdAndUserId(SAVED, ALICE)).thenReturn(Optional.empty());

        mvc.perform(delete("/api/v1/saved-searches/{id}", SAVED))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("SAVED_SEARCH_NOT_FOUND"));
    }

    @Test
    void deleting_an_owned_search_is_a_204() throws Exception {
        SavedSearch row = new SavedSearch();
        row.setUserId(ALICE);
        when(repository.findByIdAndUserId(SAVED, ALICE)).thenReturn(Optional.of(row));

        mvc.perform(delete("/api/v1/saved-searches/{id}", SAVED))
                .andExpect(status().isNoContent());

        verify(repository).delete(row);
    }

    @Test
    void a_search_with_no_criteria_is_refused() throws Exception {
        mvc.perform(post("/api/v1/saved-searches")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"Everything\",\"criteria\":{}}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_STRUCTURE_INVALID"));
    }

    @Test
    void a_blank_name_is_refused() throws Exception {
        mvc.perform(post("/api/v1/saved-searches")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\" \",\"criteria\":{\"q\":\"backend\"}}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.code").value("VALIDATION_FAILED"));
    }
}
