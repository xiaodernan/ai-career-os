package com.careeros;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Every list endpoint takes {@code page}/{@code size} straight off the query string, and
 * before {@link com.careeros.common.Paging} existed a hand-typed {@code ?page=-1} or
 * {@code ?size=0} was enough to make the server answer 500 "Internal server error": Spring's
 * {@code PageRequest} throws on both, and the job search's own {@code LIMIT :limit OFFSET
 * :offset} either went unbound or reached PostgreSQL as a negative offset. These go over real
 * HTTP so the contract is the one a browser's address bar sees, not the one a unit test
 * imagines.
 */
class PagingApiIT extends ApiIntegrationTest {

    /** Page-shaped endpoints, in the order a user meets them. */
    private static final List<String> LISTS = List.of(
            "/api/v1/jobs",
            "/api/v1/companies",
            "/api/v1/applications",
            "/api/v1/resumes",
            "/api/v1/conversations",
            "/api/v1/interview/sessions",
            "/api/v1/knowledge/sources",
            "/api/v1/knowledge/notes");

    private String bearer() throws Exception {
        return "Bearer " + register("paging-" + UUID.randomUUID() + "@example.com");
    }

    @Test
    @DisplayName("a negative page and an empty window are served, not rejected with a 500")
    void hostileWindowsAnswerWithThePageTheyActuallyServed() throws Exception {
        String auth = bearer();
        for (String path : LISTS) {
            mvc.perform(get(path).header("Authorization", auth).param("page", "-1").param("size", "0"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.data.page").value(0))
                    .andExpect(jsonPath("$.data.size").value(1))
                    .andExpect(jsonPath("$.data.items").isArray());
        }
    }

    @Test
    @DisplayName("no list lets a URL ask for more than one window of rows")
    void anOversizedRequestIsCappedWhereTheEndpointReportsItsWindow() throws Exception {
        String auth = bearer();
        for (String path : LISTS) {
            mvc.perform(get(path).header("Authorization", auth).param("size", "100000"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.data.size").value(100));
        }
    }

    @Test
    @DisplayName("a page past the end is an empty page, not an error")
    void aFarPageIsAnswerable() throws Exception {
        String auth = bearer();
        mvc.perform(get("/api/v1/jobs").header("Authorization", auth).param("page", "2000000000"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isEmpty());
    }

    @Test
    @DisplayName("the activity feed's limit is a window too")
    void theFeedCannotBeAskedForNothingOrEverything() throws Exception {
        String auth = bearer();
        mvc.perform(get("/api/v1/activity/runs").header("Authorization", auth).param("limit", "0"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").isArray());
        mvc.perform(get("/api/v1/activity/runs").header("Authorization", auth)
                        .param("limit", "-1").param("agent", "resume"))
                .andExpect(status().isOk());
    }

    /**
     * The clamp must not cost a legitimate caller anything: 0-based paging, a page in the
     * middle, and the ceiling itself all pass through untouched.
     */
    @Test
    @DisplayName("valid windows are answered exactly as asked")
    void ordinaryPagingIsUntouched() throws Exception {
        String auth = bearer();
        mvc.perform(get("/api/v1/jobs").header("Authorization", auth).param("page", "0").param("size", "12"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.page").value(0))
                .andExpect(jsonPath("$.data.size").value(12));
        mvc.perform(get("/api/v1/jobs").header("Authorization", auth).param("page", "3").param("size", "100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.page").value(3))
                .andExpect(jsonPath("$.data.size").value(100));
    }
}
