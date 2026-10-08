package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The job board's pages have to be a partition of one order, and they cannot be while the ORDER
 * BY can tie (#229). Seven roles are created here with the same title and the same salary band --
 * two sorts whose keys collide on every row -- and the board is then walked through three
 * different window sizes. Whatever window is asked for, the same seven ids have to come back in
 * the same sequence: a tie-break the plan is free to reorder between queries shows up as a
 * different sequence, a repeated row, or a row that no page ever serves.
 *
 * The SQL half of this is pinned in {@code JobSearchRepositoryTest}, where a captured statement
 * can be read without a database; this is the half a database answers.
 */
class JobBoardOrderingIT extends ApiIntegrationTest {

    private static final int ROLES = 7;

    /** One role, created through the job flow's nested-company path so the rows are shared catalog data. */
    private String createRole(String auth, String title, String companyName) throws Exception {
        Map<String, Object> request = new java.util.LinkedHashMap<>();
        request.put("title", title);
        request.put("company", Map.of("name", companyName, "industry", "ai"));
        request.put("location", "Hangzhou");
        request.put("salaryMin", 400000);
        request.put("salaryMax", 500000);
        request.put("description", "We are hiring for " + title + ".");
        MvcResult created = mvc.perform(post("/api/v1/jobs")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON).content(json(request)))
                .andReturn();
        if (created.getResponse().getStatus() != 201) {
            throw new IllegalStateException("job create answered " + created.getResponse().getStatus()
                    + ": " + created.getResponse().getContentAsString());
        }
        return created.getResponse().getContentAsString();
    }

    private static String jobId(String jobJson) throws Exception {
        return MAPPER.readTree(jobJson).path("data").path("id").asText();
    }

    /** Every id the board answers for one sort, walked one window size at a time. */
    private List<String> walk(String auth, String token, String sort, int size) throws Exception {
        List<String> ids = new ArrayList<>();
        for (int page = 0; ; page++) {
            JsonNode data = readTree(mvc.perform(get("/api/v1/jobs")
                            .header("Authorization", auth)
                            .param("q", token)
                            .param("sort", sort)
                            .param("page", String.valueOf(page))
                            .param("size", String.valueOf(size)))
                    .andExpect(status().isOk())
                    .andReturn().getResponse().getContentAsString()).path("data");
            JsonNode items = data.path("items");
            if (items.isEmpty()) {
                // The total is the whole matching set, not this window's; an empty window is the
                // end of the walk. A page the ranking skipped cannot show up as a hole here --
                // OFFSET walks contiguously -- it shows up as a row the walk never collects.
                break;
            }
            items.forEach(item -> ids.add(item.path("id").asText()));
            if (page > ROLES) {
                break;
            }
        }
        return ids;
    }

    private JsonNode readTree(String body) {
        try {
            return MAPPER.readTree(body);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @Test
    @DisplayName("every window pages the same seven tied rows in the same order")
    void everyWindowPagesTheSameRowsInTheSameOrder() throws Exception {
        String auth = "Bearer " + register("ordering-" + UUID.randomUUID() + "@example.com");
        String token = "jb" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        String company = token + " Hiring Co";
        // Every row shares one title, one company and one salary band, so `sort=title` and
        // `sort=salary` have nothing to separate them but the tie-break.
        List<String> mine = new ArrayList<>();
        for (int i = 0; i < ROLES; i++) {
            mine.add(jobId(createRole(auth, token + " Engineer", company)));
        }

        for (String sort : List.of("title", "salary", "posted")) {
            List<String> byTwo = walk(auth, token, sort, 2);
            List<String> byThree = walk(auth, token, sort, 3);
            List<String> bySeven = walk(auth, token, sort, ROLES);
            assertEquals(new LinkedHashSet<>(mine), new LinkedHashSet<>(byTwo),
                    "sort=" + sort + ": the walked pages do not cover exactly the roles created");
            assertEquals(ROLES, byTwo.size(), "sort=" + sort + ": a row was served twice");
            assertEquals(bySeven, byTwo,
                    "sort=" + sort + ": the window size changed the order the rows came back in");
            assertEquals(byThree, byTwo,
                    "sort=" + sort + ": the window size changed the order the rows came back in");
        }
    }
}
