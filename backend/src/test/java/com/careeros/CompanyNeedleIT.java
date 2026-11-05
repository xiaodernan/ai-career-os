package com.careeros;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
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
 * The company board reads a search box, and a search box holds words (58.1).
 *
 * <p>{@code GET /companies?q=} used to hand the reader's characters to Spring Data's derived
 * {@code ...Containing...} method, which wraps them in {@code %…%} itself. Two of SQL's wildcards are
 * ordinary typing -- {@code %} is on the same key as the percent sign and {@code _} is the character a
 * company name carries when its own hyphenation is an identifier -- so a percent asked for the whole
 * catalog and a mistyped underscore found a row it should not have. Neither answer is empty and neither
 * is an error, which is why this proves the matching rather than the paging: the board answered 200 the
 * whole time.
 *
 * <p>Three names under one marker no other class can collide with, and every assertion is over the
 * marker's own population, because the catalog is shared with the rest of the suite.
 */
class CompanyNeedleIT extends ApiIntegrationTest {

    private static final String PERCENT = "Per%cent";
    private static final String UNDERSCORE = "Under_Score";
    private static final String PLAIN = "Plainfield";

    private String createCompany(String auth, String companyName) throws Exception {
        mvc.perform(post("/api/v1/jobs")
                        .header("Authorization", auth)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of(
                                "title", "Engineer " + companyName,
                                "company", Map.of("name", companyName, "industry", "ai"),
                                "location", "Hangzhou",
                                "description", "We are hiring an engineer for " + companyName + "."))))
                .andExpect(status().isCreated());
        return companyName;
    }

    /** One searched page of the board, as a name list plus the total the envelope claims. */
    private JsonNode search(String auth, String q) throws Exception {
        String body = mvc.perform(get("/api/v1/companies")
                        .header("Authorization", auth)
                        .param("q", q)
                        .param("size", "50"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        try {
            return MAPPER.readTree(body).path("data");
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private List<String> names(JsonNode page) {
        List<String> out = new ArrayList<>();
        page.path("items").forEach(item -> out.add(item.path("name").asText()));
        return out;
    }

    @Test
    @DisplayName("a percent sign and an underscore in a search box are characters, not wildcards")
    void theNeedleIsMatchedAsWritten() throws Exception {
        String auth = "Bearer " + register("needle-" + UUID.randomUUID() + "@example.com");
        String token = "cn" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createCompany(auth, token + " " + PLAIN);
        createCompany(auth, token + " " + PERCENT);
        createCompany(auth, token + " " + UNDERSCORE);

        // The needle as a plain word: all three, because every name carries the marker. This is the
        // baseline the next four assertions measure against -- if the board found nothing at all, the
        // emptiness below would prove nothing.
        assertEquals(3, names(search(auth, token)).size(),
                "the marker's own three companies are not all found by the marker");

        assertEquals(List.of(token + " " + PERCENT), names(search(auth, PERCENT.toLowerCase())),
                "a percent in the box is SQL's multi-character wildcard; typed here, it has to find "
                        + "the one name that spells it");

        assertEquals(List.of(token + " " + UNDERSCORE), names(search(auth, UNDERSCORE.toLowerCase())),
                "an underscore in the box is SQL's single-character wildcard; the literal name still "
                        + "has to answer, and answering is what the old binding did by accident");

        // The two mutations the escaping prevents, asked as questions the catalog cannot answer.
        // `under_s_ore` is one mistyped character away from `under_score`, and SQL's `_` is exactly
        // that one character: the old binding found the row, so a search could return a name the
        // reader did not type.
        assertEquals(0, search(auth, token + " Under_S_ore").path("total").asInt(),
                "a mistyped underscore matched a name it does not contain -- the wildcard is still "
                        + "live in the needle");

        // And the headline: a box holding one percent sign used to answer the entire shared catalog,
        // because the wildcard was wrapped around it as well as inside it. Only the one name that
        // literally spells a percent may answer now.
        assertEquals(List.of(token + " " + PERCENT), names(search(auth, "%")),
                "a box holding only a percent sign answered something other than the one name that "
                        + "spells a percent sign");
    }

    @Test
    @DisplayName("a blank box stays the browse, and the searched branch keeps the name order")
    void anEmptyNeedleAsksNothingAndAFullOneStillPagesInOrder() throws Exception {
        String auth = "Bearer " + register("needle-" + UUID.randomUUID() + "@example.com");
        String token = "cn" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        createCompany(auth, token + " Zeta");
        createCompany(auth, token + " Alpha");

        // The catalog is shared with the rest of the suite, so "no filter" is proved by two answers
        // agreeing rather than by a total this class does not own: spaces are the empty box, and the
        // empty box is the browse the companies screen sends when nobody has typed anything yet.
        assertEquals(search(auth, "").path("total").asInt(), search(auth, "   ").path("total").asInt(),
                "a box of spaces became a search for spaces, so the browse the reader did not ask "
                        + "for answered something else");
        assertEquals(List.of(token + " Alpha", token + " Zeta"), names(search(auth, token)),
                "the searched board lost the order its pages partition by");
    }
}
