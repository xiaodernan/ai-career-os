package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

/**
 * The networking registry reads a search box, and the box holds names (70.3).
 *
 * <p>{@code GET /contacts} is the sixth list in this codebase to take a reader's word. Since 72.1
 * it answers a real page envelope, so there is a total beside the rows: a needle that matched
 * nothing is a zero total with people still in the registry, and a needle that matched five people
 * over a two-row window is a total of five, not two. Both are measured here by name, per account,
 * because an account's circle is its own -- and the count query repeats the very same needle clause,
 * so the total cannot quietly describe a different question from the rows.
 *
 * <p>The columns are the profile as the dialog writes it -- name, role, company, relation, email and
 * notes -- and five of the six are nullable, which is why every one but the name is read
 * {@code COALESCE}d: a person with no company recorded is still a person.
 */
class ContactNeedleIT extends ApiIntegrationTest {

    private static final String PERCENT = "Per%cent";
    private static final String UNDERSCORE = "Under_Score";
    private static final String PLAIN = "Plainfield";

    private void createContact(String auth, Map<String, Object> body) throws Exception {
        mvc.perform(post("/api/v1/contacts")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(body)))
                .andExpect(status().isCreated());
    }

    /** The whole answer as asked: the box as `q`, anything else as further `key, value` pairs. */
    private JsonNode answer(String auth, String q, String... extras) throws Exception {
        var request = get("/api/v1/contacts").header("Authorization", auth).param("q", q);
        for (int i = 0; i < extras.length; i += 2) {
            request = request.param(extras[i], extras[i + 1]);
        }
        String body = mvc.perform(request)
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        try {
            return MAPPER.readTree(body).path("data");
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    /** The rows of one window (72.1): the envelope's own `items`, in the route's order. */
    private JsonNode search(String auth, String q, String... extras) throws Exception {
        return answer(auth, q, extras).path("items");
    }

    /** The rows the answer carries, in its own order -- the page's order. */
    private List<String> names(JsonNode data) {
        List<String> out = new ArrayList<>();
        data.forEach(item -> out.add(item.path("name").asText()));
        return out;
    }

    @Test
    @DisplayName("a percent sign and an underscore in the registry box are characters, not wildcards")
    void theNeedleIsMatchedAsWritten() throws Exception {
        String auth = "Bearer " + register("ct-needle-" + UUID.randomUUID() + "@example.com");
        String token = "ct" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createContact(auth, Map.of("name", token + " " + PLAIN));
        createContact(auth, Map.of("name", token + " " + PERCENT));
        createContact(auth, Map.of("name", token + " " + UNDERSCORE));

        // The baseline the next four assertions measure against: if the marker found nobody, an empty
        // answer below would read as escaping rather than as a registry with three people in it.
        assertEquals(3, names(search(auth, token)).size(),
                "the marker's own three people are not all found by the marker");

        assertEquals(List.of(token + " " + PERCENT), names(search(auth, PERCENT.toLowerCase())),
                "a percent in the box is SQL's multi-character wildcard; typed here, it has to find "
                        + "the one person whose name spells it");

        assertEquals(List.of(token + " " + UNDERSCORE), names(search(auth, UNDERSCORE.toLowerCase())),
                "an underscore in the box is SQL's single-character wildcard, and the person who "
                        + "literally spells it is the only answer");

        // The mutation escaping prevents: `under_s_ore` is one mistyped character away from
        // `under_score`, and SQL's `_` is exactly one character, so an unescaped needle returns a
        // person the reader never typed.
        assertEquals(List.of(), names(search(auth, token + " Under_S_ore")),
                "a mistyped underscore matched a person it does not contain -- the wildcard is still "
                        + "live in the needle");

        // The headline this route can state without a shared catalog: the account holds three people,
        // so a box of one percent sign answers the registry only if a wildcard was wrapped around it.
        assertEquals(List.of(token + " " + PERCENT), names(search(auth, "%")),
                "a box holding only a percent sign answered something other than the one person who "
                        + "spells a percent sign");
    }

    @Test
    @DisplayName("the box reads every column the profile owns, including the five that may be absent")
    void theNeedleReachesEveryColumnTheProfileOwns() throws Exception {
        String auth = "Bearer " + register("ct-needle-" + UUID.randomUUID() + "@example.com");
        String token = "col" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        // One person per column, none of them named with the marker: a name-only search would answer
        // one row out of five and look like a registry that simply has few people in it.
        createContact(auth, Map.of("name", "Ada", "role", token + " Staff Engineer"));
        createContact(auth, Map.of("name", "Bo", "company", token + " Northwind"));
        createContact(auth, Map.of("name", "Cy", "relation", token + " recruiter"));
        createContact(auth, Map.of("name", "Dee", "email", token + "@acme.dev"));
        createContact(auth, Map.of("name", "Eli", "notes", "met " + token + " at the conference"));
        createContact(auth, Map.of("name", "Fern"));

        List<String> found = names(search(auth, token));
        assertEquals(5, found.size(),
                "the box read one column: a person whose role, company, relation, email or notes spell "
                        + "the word is a person the reader is looking for");
        assertTrue(found.containsAll(List.of("Ada", "Bo", "Cy", "Dee", "Eli")),
                "the answer named someone other than the five: " + found);
        assertTrue(!found.contains("Fern"),
                "a person carrying none of the word was answered, so the needle is still a wildcard");

        // The nullable five really are nullable: an account whose people have only names is searchable
        // by those names, which is what a COALESCE around an absent column has to keep true.
        assertEquals(List.of("Ada"), names(search(auth, "ada")),
                "a profile with four absent columns could not be found by the one column it has");
    }

    @Test
    @DisplayName("an empty box is the whole registry, a box of spaces is the empty box")
    void aBlankNeedleAsksNothing() throws Exception {
        String auth = "Bearer " + register("ct-needle-" + UUID.randomUUID() + "@example.com");
        String token = "blk" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createContact(auth, Map.of("name", token + " Zeta"));
        createContact(auth, Map.of("name", token + " Alpha"));

        // The page sends the empty box before anyone types, so an empty needle that filtered would open
        // on nothing -- and a box of spaces is the same box the reader has not typed in.
        assertEquals(2, names(search(auth, "")).size(),
                "a box nobody typed in became a filter and emptied the registry");
        assertEquals(2, names(search(auth, "   ")).size(),
                "spaces became a search for spaces, so the browse the reader did not ask for "
                        + "answered something else");

        // Caps lock costs the reader their own circle: the needle is lower-cased once per request, the
        // columns are lower-cased per row, and both answers are the two people.
        assertEquals(2, names(search(auth, token.toUpperCase())).size(),
                "the box matched case-sensitively, so a word typed with Shift found nobody");
    }

    @Test
    @DisplayName("a window holds part of the matches while total counts all of them")
    void theWindowCountsTheMatchesNotThePage() throws Exception {
        String auth = "Bearer " + register("ct-page-" + UUID.randomUUID() + "@example.com");
        String token = "pg" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        for (int i = 0; i < 5; i++) {
            createContact(auth, Map.of("name", token + " person " + i));
        }
        createContact(auth, Map.of("name", "someone else entirely"));

        JsonNode first = answer(auth, token, "size", "2", "page", "0");
        assertEquals(5, first.path("total").asInt(),
                "total must count the people who spell the word, not the rows this window holds");
        assertEquals(2, first.path("items").size(), "the first window holds two rows");
        assertEquals(0, first.path("page").asInt(), "the answer carries the page the server used");
        assertEquals(2, first.path("size").asInt(), "the answer carries the window the server used");

        // Three disjoint windows over five matches, so the id tiebreaker and the count query are
        // both proven against real Postgres rather than against a mocked repository.
        List<String> seen = new ArrayList<>(names(first.path("items")));
        seen.addAll(names(answer(auth, token, "size", "2", "page", "1").path("items")));
        JsonNode last = answer(auth, token, "size", "2", "page", "2");
        assertEquals(1, last.path("items").size(), "five matches over a window of two is three pages");
        seen.addAll(names(last.path("items")));
        assertEquals(5, seen.size(), "the three windows together hold every match");
        assertEquals(5L, seen.stream().distinct().count(),
                "a person appeared on two pages -- the total order broke across the window");

        JsonNode beyond = answer(auth, token, "size", "2", "page", "9");
        assertEquals(0, beyond.path("items").size(), "a page past the end is an empty window");
        assertEquals(5, beyond.path("total").asInt(),
                "an empty window is not an empty answer: the matches still exist");

        // The same clamp the other boards get: a bookmarked typo is an answerable request, not a 500.
        JsonNode clamped = answer(auth, token, "size", "5000", "page", "-1");
        assertEquals(0, clamped.path("page").asInt(), "a negative page is floored to the first one");
        assertEquals(100, clamped.path("size").asInt(), "a huge window is clamped to the ceiling");
        assertEquals(5, clamped.path("items").size(), "the clamped first page still holds every match");
    }
}
