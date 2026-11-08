package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The shelf answers the filter panel, not the whole bookmark list (74.1).
 *
 * <p>{@code GET /jobs/saved} used to bind nothing: it answered every bookmark and the browser
 * narrowed the answer with its own copy of the board's rules. That copy could only ever be
 * narrower, and it was -- a word reached title and company on the Saved tab and title, company
 * <em>and</em> description on Discover, so the same box in the same screen answered two different
 * questions. The route now reads the same predicate fragment the discover board reads, and this
 * class measures the three things that claim needs a database for: which columns a word can reach,
 * what each panel control does to the shelf, and whose bookmarks a shelf can contain.
 *
 * <p>The fragment itself is pinned without a database in {@code JobSearchRepositoryTest}, which
 * compares the two statements clause for clause; what belongs here is the answer, because
 * {@code j.tsv} is a generated column and its tokenisation is not something a captured string can
 * speak for. Comparisons are set comparisons on purpose: the order the shelf comes back in is 74.2's
 * claim, and a set is the half that is true today.
 */
class SavedJobBoardIT extends ApiIntegrationTest {

    private String createRole(String auth, Map<String, Object> body) throws Exception {
        Map<String, Object> request = new LinkedHashMap<>(body);
        request.putIfAbsent("location", "Hangzhou");
        request.putIfAbsent("description", "We are hiring.");
        MvcResult created = mvc.perform(post("/api/v1/jobs")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON).content(json(request)))
                .andReturn();
        if (created.getResponse().getStatus() != 201) {
            throw new IllegalStateException("job create answered " + created.getResponse().getStatus()
                    + ": " + created.getResponse().getContentAsString());
        }
        return MAPPER.readTree(created.getResponse().getContentAsString())
                .path("data").path("id").asText();
    }

    private void bookmark(String auth, String jobId, String note) throws Exception {
        mvc.perform(post("/api/v1/jobs/" + jobId + "/save")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("note", note))))
                .andExpect(status().isOk());
    }

    private JsonNode shelf(String auth, String... extras) throws Exception {
        var request = get("/api/v1/jobs/saved").header("Authorization", auth);
        for (int i = 0; i < extras.length; i += 2) {
            request = request.param(extras[i], extras[i + 1]);
        }
        return MAPPER.readTree(mvc.perform(request).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString()).path("data");
    }

    private List<String> shelfIds(String auth, String... extras) throws Exception {
        List<String> ids = new ArrayList<>();
        shelf(auth, extras).forEach(item -> ids.add(item.path("job").path("id").asText()));
        return ids;
    }

    private static Set<String> setOf(List<String> ids) {
        return new LinkedHashSet<>(ids);
    }

    /** The discover board's window over the same predicates, collected whole. */
    private List<String> boardIds(String auth, String... extras) throws Exception {
        List<String> all = new ArrayList<>();
        var request = get("/api/v1/jobs").header("Authorization", auth).param("size", "100");
        for (int i = 0; i < extras.length; i += 2) {
            request = request.param(extras[i], extras[i + 1]);
        }
        JsonNode items = MAPPER.readTree(mvc.perform(request).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString()).path("data").path("items");
        items.forEach(item -> all.add(item.path("id").asText()));
        return all;
    }

    @Test
    @DisplayName("the word in the box means the same thing on the shelf and on the board")
    void theSameWordAnswersTheSameRolesOnBothTabs() throws Exception {
        String auth = "Bearer " + register("saved-board-" + UUID.randomUUID() + "@example.com");
        String token = "sb" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        String company = token + " Hiring Co";
        // Four roles, one search word, and the word placed where the browser's copy of the filter
        // could not reach it: in the description body. The fourth puts it in the company name, which
        // is in no tsv at all and reachable only through the join the shelf now performs.
        String byDescription = createRole(auth, Map.of("title", token + " Backend Engineer",
                "company", Map.of("name", company, "industry", "ai"),
                "description", "Owns the kafka pipeline and its alerts."));
        String byTitle = createRole(auth, Map.of("title", token + " Kafka Platform Engineer",
                "company", Map.of("name", company, "industry", "ai"),
                "description", "Leads the ingestion team."));
        String noWord = createRole(auth, Map.of("title", token + " SRE",
                "company", Map.of("name", company, "industry", "ai"),
                "description", "Runs the cluster and nothing else."));
        String byCompany = createRole(auth, Map.of("title", token + " Data Engineer",
                "company", Map.of("name", token + " Kafka Works", "industry", "ai"),
                "description", "Builds the dashboards."));
        for (String id : List.of(byDescription, byTitle, noWord, byCompany)) {
            bookmark(auth, id, "note");
        }

        Set<String> board = setOf(boardIds(auth, "q", token + " kafka"));
        Set<String> shelf = setOf(shelfIds(auth, "q", token + " kafka"));

        assertEquals(setOf(List.of(byDescription, byTitle, byCompany)), board,
                "the board itself does not answer the three roles that spell the word, so the "
                        + "baseline this case compares against is the wrong one");
        assertEquals(board, shelf,
                "the same box on the same screen answered two different sets of roles: the shelf "
                        + "is still deciding which rows match for itself");
        // Spelled out separately because a shelf that answered all four bookmarks would pass the
        // comparison above only if the board had drifted too -- and the drift is what is being asked
        // about.
        assertTrue(!shelf.contains(noWord), "a role carrying none of the word was kept by the shelf");
    }

    @Test
    @DisplayName("every control on the panel narrows the shelf")
    void everyPanelControlNarrowsTheShelf() throws Exception {
        String auth = "Bearer " + register("saved-panel-" + UUID.randomUUID() + "@example.com");
        String token = "sp" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        // Two roles that differ on one column each, so every assertion names the row it keeps.
        // Salaries are the band's own minor units, as the create route takes them.
        String javaOnsite = createRole(auth, Map.of("title", token + " Java Shop Role",
                "company", Map.of("name", token + " First Co", "industry", "ai"),
                "location", "Hangzhou", "remoteType", "onsite", "skills", List.of("java"),
                "salaryMin", 100000, "salaryMax", 150000,
                "description", "Keeps the old services running."));
        String springRemote = createRole(auth, Map.of("title", token + " Spring Cloud Role",
                "company", Map.of("name", token + " Second Co", "industry", "ai"),
                "location", "Shanghai", "remoteType", "remote", "skills", List.of("spring", "kafka"),
                "salaryMin", 400000, "salaryMax", 500000,
                "description", "Builds the new platform."));
        for (String id : List.of(javaOnsite, springRemote)) {
            bookmark(auth, id, "kept");
        }

        assertEquals(setOf(List.of(javaOnsite, springRemote)), setOf(shelfIds(auth)),
                "an empty panel became a filter, so the shelf nobody narrowed answered less than "
                        + "the bookmarks the reader keeps");

        assertEquals(List.of(springRemote), shelfIds(auth, "location", "Shanghai"),
                "the location control did not narrow the shelf");
        assertEquals(List.of(javaOnsite), shelfIds(auth, "remote", "onsite"),
                "the remote control did not narrow the shelf");
        assertEquals(List.of(springRemote), shelfIds(auth, "skills", "spring"),
                "the skills control did not narrow the shelf");
        assertEquals(List.of(javaOnsite), shelfIds(auth, "skills", "java"),
                "a skill the shelf holds once answered twice -- the skill array is not being read");
        assertEquals(List.of(springRemote), shelfIds(auth, "minSalary", "200000"),
                "a floor of 200000 kept a role whose band tops out at 150000");
        assertEquals(List.of(javaOnsite), shelfIds(auth, "maxSalary", "200000"),
                "a ceiling of 200000 kept a role whose band starts at 400000");
        assertEquals(List.of(springRemote), shelfIds(auth, "company", "Second Co"),
                "the company control did not narrow the shelf");

        // Two controls are one question, not two reads: the panel sends them together.
        assertEquals(List.of(), shelfIds(auth, "location", "Shanghai", "remote", "onsite"),
                "two controls no single role satisfies answered a role anyway");
        assertEquals(List.of(springRemote), shelfIds(auth, "location", "Shanghai", "skills", "kafka"),
                "two controls one role satisfies answered nothing");
    }

    @Test
    @DisplayName("a shelf holds its reader's bookmarks and no other account's")
    void theShelfIsScopedToItsReader() throws Exception {
        String auth = "Bearer " + register("saved-scope-" + UUID.randomUUID() + "@example.com");
        String stranger = "Bearer " + register("saved-scope-" + UUID.randomUUID() + "@example.com");
        String token = "ss" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        String company = token + " Shared Co";
        String mineAlone = createRole(auth, Map.of("title", token + " Only Mine",
                "company", Map.of("name", company, "industry", "ai")));
        String bothKeep = createRole(auth, Map.of("title", token + " Kept By Both",
                "company", Map.of("name", company, "industry", "ai")));
        bookmark(auth, mineAlone, "mine");
        bookmark(auth, bothKeep, "mine");
        // The postings are the shared catalogue, so the stranger can bookmark the very same row.
        bookmark(stranger, bothKeep, "theirs");

        assertEquals(setOf(List.of(mineAlone, bothKeep)), setOf(shelfIds(auth, "q", token)),
                "the reader's own shelf is not whole");
        assertEquals(List.of(bothKeep), shelfIds(stranger, "q", token),
                "one account's bookmark of a shared posting reached another account's shelf");
        // The note belongs to the bookmark, not the posting: the same row kept twice says twice.
        assertEquals("theirs", shelf(stranger, "q", token).get(0).path("note").asText(),
                "the answer carried someone else's note");
        assertEquals(List.of(), shelfIds(auth, "q", token + " nonexistent"),
                "a word nothing spells answered a bookmark anyway");
    }

    @Test
    @DisplayName("a percent sign and an underscore in the shelf box are characters")
    void theNeedleIsCharactersOnTheShelfToo() throws Exception {
        String auth = "Bearer " + register("saved-needle-" + UUID.randomUUID() + "@example.com");
        String token = "sn" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        String company = token + " Hiring Co";
        String percent = createRole(auth, Map.of("title", token + " Per%cent Role",
                "company", Map.of("name", company, "industry", "ai")));
        String percentage = createRole(auth, Map.of("title", token + " Percentage Role",
                "company", Map.of("name", company, "industry", "ai")));
        String underscore = createRole(auth, Map.of("title", token + " Under_Score Role",
                "company", Map.of("name", company, "industry", "ai")));
        String underX = createRole(auth, Map.of("title", token + " UnderXScore Role",
                "company", Map.of("name", company, "industry", "ai")));
        for (String id : List.of(percent, percentage, underscore, underX)) {
            bookmark(auth, id, "kept");
        }

        assertEquals(4, shelfIds(auth, "q", token).size(),
                "the marker's own four roles are not all on the shelf");
        // With a live wildcard the pattern is `%token per%cent%`, and "percentage" satisfies it --
        // the mutation this pins is a role the reader never typed coming back.
        assertEquals(List.of(percent), shelfIds(auth, "q", token + " per%cent"),
                "a percent sign in the box acted as SQL's multi-character wildcard");
        // Spelled the way the role spells it: `_` as a live wildcard is one character, so the
        // pattern would also reach "UnderXScore" -- a second role the reader never named.
        assertEquals(List.of(underscore), shelfIds(auth, "q", token + " under_score"),
                "an underscore in the box acted as SQL's single-character wildcard");
        // The box holding only a wildcard is the loudest form of the same defect: one character
        // typed, and the shelf answers everything it keeps.
        assertEquals(List.of(percent), shelfIds(auth, "q", "%"),
                "a box of one percent sign answered a role that does not spell a percent sign");
    }
}
