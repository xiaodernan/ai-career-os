package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
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
 * The pipeline board reads a search box, and a search box holds words (70.1).
 *
 * <p>{@code GET /applications?q=} had no box beside it until now, so nothing proved what the
 * board's four sibling routes had to be taught one at a time: a needle built with Spring Data's
 * derived {@code ...Containing...} is wrapped in {@code %…%} by the framework, which turns two
 * ordinary keystrokes into SQL's wildcards. This route adds a second hazard the company board did
 * not have -- it filters on three columns and the reader's word may be in any of them -- so a
 * wrong answer here is a card that is on the board but not in the window the reader asked for.
 *
 * <p>Every assertion is scoped to one freshly registered account, because an account's pipeline is
 * its own: unlike the shared company catalog, the total this class measures is the total it filed.
 */
class ApplicationNeedleIT extends ApiIntegrationTest {

    private static final String PERCENT = "Per%cent";
    private static final String UNDERSCORE = "Under_Score";
    private static final String PLAIN = "Plainfield";

    private void createApplication(String auth, Map<String, Object> body) throws Exception {
        mvc.perform(post("/api/v1/applications")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(body)))
                .andExpect(status().isCreated());
    }

    /** One page of the board: the box as `q`, anything else as further `key, value` pairs. */
    private JsonNode search(String auth, String q, String... extras) throws Exception {
        var request = get("/api/v1/applications")
                .header("Authorization", auth)
                .param("q", q)
                .param("size", "50");
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

    /** The page's cards, in the order the answer puts them -- the board's row order. */
    private List<String> titles(JsonNode page) {
        List<String> out = new ArrayList<>();
        page.path("items").forEach(item -> out.add(item.path("title").asText()));
        return out;
    }

    @Test
    @DisplayName("a percent sign and an underscore in the pipeline box are characters, not wildcards")
    void theNeedleIsMatchedAsWritten() throws Exception {
        String auth = "Bearer " + register("app-needle-" + UUID.randomUUID() + "@example.com");
        String token = "ap" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createApplication(auth, Map.of("title", token + " " + PLAIN));
        createApplication(auth, Map.of("title", token + " " + PERCENT));
        createApplication(auth, Map.of("title", token + " " + UNDERSCORE));

        // The baseline the next four assertions measure against: if the marker found nothing, an
        // empty answer below would look like escaping rather than a board with no rows.
        assertEquals(3, titles(search(auth, token)).size(),
                "the marker's own three cards are not all found by the marker");

        assertEquals(List.of(token + " " + PERCENT), titles(search(auth, PERCENT.toLowerCase())),
                "a percent in the box is SQL's multi-character wildcard; typed here, it has to find "
                        + "the one card that spells it");

        assertEquals(List.of(token + " " + UNDERSCORE), titles(search(auth, UNDERSCORE.toLowerCase())),
                "an underscore in the box is SQL's single-character wildcard, and the card that "
                        + "literally spells it is the only answer");

        // The mutation escaping prevents: `under_s_ore` is one mistyped character away from
        // `under_score`, and SQL's `_` is exactly one character, so the old binding would have
        // returned a card the reader never typed.
        assertEquals(0, search(auth, token + " Under_S_ore").path("total").asInt(),
                "a mistyped underscore matched a card it does not contain -- the wildcard is still "
                        + "live in the needle");

        // And the headline, which needs no shared catalog to prove: this account holds three cards
        // and nothing else, so a box of one percent sign answers the board only if the wildcard is
        // wrapped around it. One card answers.
        assertEquals(List.of(token + " " + PERCENT), titles(search(auth, "%")),
                "a box holding only a percent sign answered something other than the one card that "
                        + "spells a percent sign");
    }

    @Test
    @DisplayName("the box reads the card's company and notes, and a status narrows the same answer")
    void theNeedleReachesEveryColumnTheCardOwns() throws Exception {
        String auth = "Bearer " + register("app-needle-" + UUID.randomUUID() + "@example.com");
        String token = "co" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createApplication(auth, Map.of("title", "Backend Engineer",
                "companyName", token + " Northwind", "status", "interview"));
        createApplication(auth, Map.of("title", "Data Engineer",
                "notes", "asked " + token + " for a referral", "status", "interview"));
        createApplication(auth, Map.of("title", "Platform Engineer", "status", "saved"));

        // Neither card is titled with the marker, so both halves of the answer are cards a
        // title-only search would have lost.
        assertEquals(2, search(auth, token).path("total").asInt(),
                "the box read one column: a card whose company or notes spell the word is a card "
                        + "the reader is looking for");

        // Asked beside a column, the answer is that column's own order -- the position the reader
        // arranged, `saved`-first being card 0 -- and not a third order the search invented.
        assertEquals(List.of("Backend Engineer", "Data Engineer"),
                titles(search(auth, token, "status", "interview")),
                "the box beside a status either dropped the column or re-sorted it");

        // Both narrowings, or the box would be a second way of asking for the whole board.
        assertEquals(0, search(auth, token, "status", "saved").path("total").asInt(),
                "a status beside the box was dropped, so the column answered the whole board");
    }

    @Test
    @DisplayName("an empty box is the whole board, a box of spaces is the empty box")
    void aBlankNeedleAsksNothing() throws Exception {
        String auth = "Bearer " + register("app-needle-" + UUID.randomUUID() + "@example.com");
        String token = "bl" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createApplication(auth, Map.of("title", token + " Zeta"));
        createApplication(auth, Map.of("title", token + " Alpha"));

        // The board sends the empty box before anyone types, so an empty needle that filtered
        // would open on nothing -- and a box of spaces is the same box the reader has not typed in.
        assertEquals(2, search(auth, "").path("total").asInt(),
                "a box nobody typed in became a filter and emptied the board");
        assertEquals(2, search(auth, "   ").path("total").asInt(),
                "spaces became a search for spaces, so the browse the reader did not ask for "
                        + "answered something else");

        // Caps lock costs the reader their own pipeline: the needle is lower-cased once, the column
        // is lower-cased per row, and both answers are the two cards.
        assertEquals(2, search(auth, token.toUpperCase()).path("total").asInt(),
                "the box matched case-sensitively, so a word typed with Shift found nothing");
    }
}
