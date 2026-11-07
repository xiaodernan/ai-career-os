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
 * The rehearsals board reads a search box, and the box holds the words a rehearsal was named with
 * (70.4).
 *
 * <p>This list arrived as two derived Spring Data methods that differed only by whether a card id
 * had been set, so a reader's word would have made them four. They are one query now, and the two
 * scopes inside it are the reason this class measures more than escaping: the user is always the
 * first scope, the card id is a second one on top of it, and the word narrows what is left. A
 * foreign card id has to answer an empty page rather than somebody else's practice.
 *
 * <p>The columns are the session's own -- company, position and mode -- not the turns it contains.
 * Two of the three are nullable by construction: a rehearsal started free-form records no company,
 * and one started from a posting may record no position of its own. Those rows still have to answer
 * a word typed into the column they do have, which is what the {@code COALESCE} around them is for.
 */
class InterviewNeedleIT extends ApiIntegrationTest {

    private static final String PERCENT = "Per%cent";
    private static final String UNDERSCORE = "Under_Score";
    private static final String PLAIN = "Plainfield";

    private String createSession(String auth, Map<String, Object> body) throws Exception {
        String result = mvc.perform(post("/api/v1/interview/sessions")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(body)))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        try {
            return MAPPER.readTree(result).path("data").path("id").asText();
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    /** The whole answer as asked: the box as `q`, anything else as further `key, value` pairs. */
    private JsonNode answer(String auth, String q, String... extras) throws Exception {
        var request = get("/api/v1/interview/sessions")
                .header("Authorization", auth)
                .param("q", q);
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

    /** The rows of one window, in the route's own order -- newest start first, id breaking the tie. */
    private List<String> positions(JsonNode page) {
        List<String> out = new ArrayList<>();
        page.path("items").forEach(item -> out.add(item.path("positionTitle").asText()));
        return out;
    }

    @Test
    @DisplayName("a percent sign and an underscore in the rehearsals box are characters, not wildcards")
    void theNeedleIsMatchedAsWritten() throws Exception {
        String auth = "Bearer " + register("iv-needle-" + UUID.randomUUID() + "@example.com");
        String token = "iv" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createSession(auth, Map.of("positionTitle", token + " " + PLAIN));
        createSession(auth, Map.of("positionTitle", token + " " + PERCENT));
        createSession(auth, Map.of("positionTitle", token + " " + UNDERSCORE));

        // The baseline the next four assertions measure against: if the marker found nothing, an
        // empty answer below would read as escaping rather than as a board with no rehearsals.
        assertEquals(3, positions(answer(auth, token)).size(),
                "the marker's own three rehearsals are not all found by the marker");

        assertEquals(List.of(token + " " + PERCENT), positions(answer(auth, PERCENT.toLowerCase())),
                "a percent in the box is SQL's multi-character wildcard; typed here, it has to find "
                        + "the one rehearsal whose position spells it");

        assertEquals(List.of(token + " " + UNDERSCORE), positions(answer(auth, UNDERSCORE.toLowerCase())),
                "an underscore in the box is SQL's single-character wildcard, and the rehearsal that "
                        + "literally spells it is the only answer");

        // The mutation escaping prevents: `Under_S_ore` is one mistyped character away from
        // `Under_Score`, and SQL's `_` is exactly one character, so a live wildcard returns a
        // rehearsal the reader never typed.
        assertEquals(List.of(), positions(answer(auth, token + " Under_S_ore")),
                "a mistyped underscore matched a rehearsal it does not contain -- the wildcard is "
                        + "still live in the needle");

        // The headline this route can state without a shared catalog: the account holds three
        // rehearsals, so a box of one percent sign answers all three only if a wildcard was wrapped.
        assertEquals(List.of(token + " " + PERCENT), positions(answer(auth, "%")),
                "a box holding only a percent sign answered something other than the one rehearsal "
                        + "that spells a percent sign");
    }

    @Test
    @DisplayName("the box reads the rehearsal's own three columns, including the two it may leave empty")
    void theNeedleReachesEveryColumnTheSessionOwns() throws Exception {
        String auth = "Bearer " + register("iv-needle-" + UUID.randomUUID() + "@example.com");
        String token = "col" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        // One rehearsal per text column, and one with neither: a company-only search would answer
        // one row out of three and look like a board that simply has few rehearsals on it.
        String byPosition = createSession(auth, Map.of("positionTitle", token + " Staff Engineer",
                "mode", "behavioral"));
        createSession(auth, Map.of("companyName", token + " Northwind",
                "positionTitle", "A", "mode", "technical"));
        createSession(auth, Map.of("positionTitle", "C"));

        List<String> found = positions(answer(auth, token));
        assertEquals(2, found.size(),
                "the box read one column: a rehearsal whose company or position spells the word is "
                        + "a rehearsal the reader is looking for");
        assertTrue(found.containsAll(List.of("A", token + " Staff Engineer")),
                "the answer named something other than the two: " + found);
        assertTrue(!found.contains("C"),
                "a rehearsal carrying none of the word was answered, so the needle is still a wildcard");

        // `mode` is the third column and the only one the schema refuses to leave empty, so it is
        // also the way a rehearsal with no company and no position of its own can still be found.
        assertEquals(List.of("A"), positions(answer(auth, "technical")),
                "the box never read the mode column");
        assertEquals(List.of(token + " Staff Engineer"), positions(answer(auth, "behavioral")),
                "a mode typed into the box found nothing");
        assertEquals(List.of("C"), positions(answer(auth, "mixed")),
                "a rehearsal with both text columns absent could not be found by the one column it "
                        + "has -- an absent column dropped the row instead of missing the word");

        // The two searches are one read, not two: the same word narrows the same rows however the
        // reader spelled the case.
        assertEquals(2, positions(answer(auth, token.toUpperCase())).size(),
                "the box matched case-sensitively, so a word typed with Shift found nobody");
        assertEquals(byPosition, answer(auth, token + " staff").path("items").get(0).path("id").asText(),
                "a phrase spanning the position column stopped matching partway through");
    }

    @Test
    @DisplayName("an empty box is the whole history, a box of spaces is the empty box")
    void aBlankNeedleAsksNothing() throws Exception {
        String auth = "Bearer " + register("iv-needle-" + UUID.randomUUID() + "@example.com");
        String token = "blk" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createSession(auth, Map.of("positionTitle", token + " Zeta"));
        createSession(auth, Map.of("positionTitle", token + " Alpha"));

        // The page sends the empty box before anyone types, so an empty needle that filtered would
        // open on nothing -- and a box of spaces is the same box the reader has not typed in.
        assertEquals(2, positions(answer(auth, "")).size(),
                "a box nobody typed in became a filter and emptied the history");
        assertEquals(2, positions(answer(auth, "   ")).size(),
                "spaces became a search for spaces, so the browse the reader did not ask for "
                        + "answered something else");
    }

    @Test
    @DisplayName("the card id and the word narrow the same read, and a foreign card answers nothing")
    void theTwoScopesNarrowOneQuery() throws Exception {
        String auth = "Bearer " + register("iv-needle-" + UUID.randomUUID() + "@example.com");
        String token = "scope" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
        String card = createCard(auth, token + " Card");
        String other = createCard(auth, "Another card");
        createSession(auth, Map.of("applicationId", card, "positionTitle", token + " On Card"));
        createSession(auth, Map.of("applicationId", card, "positionTitle", "Unrelated"));
        createSession(auth, Map.of("positionTitle", token + " Free Practice"));

        assertEquals(List.of(token + " On Card"), positions(answer(auth, token, "applicationId", card)),
                "the word and the card id did not narrow the same read");
        assertEquals(2, positions(answer(auth, token)).size(),
                "the word alone has to find the card's rehearsal and the free one");
        assertEquals(2, positions(answer(auth, "", "applicationId", card)).size(),
                "the card id alone has to keep answering both of its rehearsals");
        assertEquals(List.of(), positions(answer(auth, token, "applicationId", other)),
                "a card that owns no rehearsal spelling the word answered one anyway");

        // Somebody else's card id is a guess, and a guess finds nothing: the user scope is under the
        // card scope, never replaced by it.
        String stranger = "Bearer " + register("iv-needle-" + UUID.randomUUID() + "@example.com");
        assertEquals(0, answer(stranger, token, "applicationId", card).path("total").asInt(),
                "another account's rehearsals were answered to a guessed card id");
        assertEquals(0, answer(stranger, "").path("total").asInt(),
                "the history is per account, and a fresh one has none");
    }

    private String createCard(String auth, String title) throws Exception {
        String result = mvc.perform(post("/api/v1/applications")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("title", title))))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        try {
            return MAPPER.readTree(result).path("data").path("id").asText();
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @Test
    @DisplayName("a window holds part of the matches while total counts all of them")
    void theWindowCountsTheMatchesNotThePage() throws Exception {
        String auth = "Bearer " + register("iv-page-" + UUID.randomUUID() + "@example.com");
        String token = "pg" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        for (int i = 0; i < 5; i++) {
            createSession(auth, Map.of("positionTitle", token + " rehearsal " + i));
        }
        createSession(auth, Map.of("positionTitle", "something else entirely"));

        JsonNode first = answer(auth, token, "size", "2", "page", "0");
        assertEquals(5, first.path("total").asInt(),
                "total must count the rehearsals that spell the word, not the rows this window holds");
        assertEquals(2, first.path("items").size(), "the first window holds two rows");
        assertEquals(0, first.path("page").asInt(), "the answer carries the page the server used");
        assertEquals(2, first.path("size").asInt(), "the answer carries the window the server used");

        // Three disjoint windows over five matches, so the id tiebreaker and the count query the
        // @Query derives are both proven against real Postgres rather than a mocked repository.
        List<String> seen = new ArrayList<>(positions(first));
        seen.addAll(positions(answer(auth, token, "size", "2", "page", "1")));
        JsonNode last = answer(auth, token, "size", "2", "page", "2");
        assertEquals(1, last.path("items").size(), "five matches over a window of two is three pages");
        seen.addAll(positions(last));
        assertEquals(5, seen.size(), "the three windows together hold every match");
        assertEquals(5L, seen.stream().distinct().count(),
                "a rehearsal appeared on two pages -- the total order broke across the window");

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