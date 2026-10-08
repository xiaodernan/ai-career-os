package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

/**
 * The company board's pages have to partition the catalog, and they cannot do that while the row
 * order is whichever one the database feels like returning (#227).
 *
 * <p>Both list branches carry their order now -- {@code findAllByOrderByNameAsc} for the browse
 * and {@code findByNameContainingIgnoreCaseOrderByNameAsc} for {@code ?q=} -- so this proves the
 * property that ordering buys rather than the SQL that spells it: every page is a slice of one
 * alphabet, no company is served twice, and none falls between two pages. Companies are shared
 * catalog data, so the seven rows created here carry a token no other test class can collide
 * with, and the unfiltered assertions compare a page against its neighbour instead of against a
 * total the suite does not own.
 */
class CompanyOrderingIT extends ApiIntegrationTest {

    /** Seven deliberately non-alphabetical names behind one marker, so the order has to be earned. */
    private static final List<String> SUFFIXES =
            List.of("Zephyr", "Acme", "Mosaic", "Borealis", "Cobalt", "Delta", "Aurora");

    private void createCompany(String auth, String companyName) throws Exception {
        mvc.perform(post("/api/v1/jobs")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of(
                                "title", "Engineer " + companyName,
                                "company", Map.of("name", companyName, "industry", "ai"),
                                "location", "Hangzhou",
                                "description", "We are hiring an engineer for " + companyName + "."))))
                .andExpect(status().isCreated());
    }

    private List<String> names(String pageJson) {
        JsonNode items = readTree(pageJson).path("data").path("items");
        List<String> out = new ArrayList<>();
        items.forEach(item -> out.add(item.path("name").asText()));
        return out;
    }

    private JsonNode readTree(String body) {
        try {
            return MAPPER.readTree(body);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    /** One page of the board; an empty {@code q} is the browse the companies screen sends. */
    private List<String> pageNames(String auth, String q, int page, int size) throws Exception {
        String body = mvc.perform(get("/api/v1/companies")
                        .header("Authorization", auth)
                        .param("q", q)
                        .param("page", String.valueOf(page))
                        .param("size", String.valueOf(size)))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        return names(body);
    }

    @Test
    @DisplayName("pages of companies are slices of one alphabet, searched or browsed")
    void pagesPartitionTheCatalogByName() throws Exception {
        String auth = "Bearer " + register("ordering-" + UUID.randomUUID() + "@example.com");
        String token = "co" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        List<String> mine = SUFFIXES.stream().map(s -> token + " " + s).collect(Collectors.toList());
        for (String name : mine) {
            createCompany(auth, name);
        }

        assertEquals(List.of(mine.get(1), mine.get(6)), pageNames(auth, token, 0, 2),
                "the first two rows of the searched board are not its two alphabetically first companies");

        // Walk the searched board two rows at a time and collect it whole: seven rows, seven
        // distinct names, an odd tail page, and the order the walk hands them back is the
        // alphabetical one. A missing order shows up here as a repeat, a gap, or an unsorted page.
        List<String> walked = new ArrayList<>();
        for (int page = 0; page * 2 < mine.size(); page++) {
            walked.addAll(pageNames(auth, token, page, 2));
        }
        assertEquals(mine.size(), walked.size(),
                "seven companies were paged over two at a time: a repeat or a gap is a page that "
                        + "does not partition the catalog");
        assertEquals(mine.stream().sorted().collect(Collectors.toList()), walked,
                "the walked pages are not in ascending name order, so the searched board's pages "
                        + "are not slices of one alphabet");

        // One past the end is an empty window over a real total, not an error and not a repeat.
        mvc.perform(get("/api/v1/companies").header("Authorization", auth)
                        .param("q", token).param("page", "4").param("size", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items").isEmpty())
                .andExpect(jsonPath("$.data.total").value(mine.size()));

        // The unfiltered browse carries the same order, and the next page continues this one
        // instead of restarting: this board shares the catalog with whatever else the suite has
        // created, so the check is between neighbours rather than against a known total.
        List<String> first = pageNames(auth, "", 0, 5);
        List<String> next = pageNames(auth, "", 1, 5);
        assertEquals(first.stream()
                        .sorted(Comparator.comparing(name -> name.toLowerCase(Locale.ROOT)))
                        .collect(Collectors.toList()),
                first, "the unfiltered board's first page is not in ascending name order");
        assertTrue(first.isEmpty() || next.isEmpty()
                        || first.get(first.size() - 1).compareToIgnoreCase(next.get(0)) < 0,
                () -> "page 1 restarts the alphabet instead of continuing it: "
                        + first.get(first.size() - 1) + " then " + next.get(0));
    }
}
