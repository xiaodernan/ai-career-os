package com.careeros.job.connector;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

/**
 * The addresses a Lever board is known by (roadmap 19.8): a company token, a public
 * board page, or the API URL. The EU tenants are the same shape on their own hosts, and
 * a page read from {@code jobs.eu.lever.co} is fetched from {@code api.eu.lever.co}.
 * {@code mode=json} is what makes the endpoint answer a payload rather than a page, so
 * an API URL that names no mode gets it added.
 */
class LeverConnectorTest {

    private static final String API = "https://api.lever.co/v0/postings/";
    private final LeverConnector connector = new LeverConnector();

    @Test
    void a_token_becomes_the_postings_endpoint() {
        assertThat(connector.apiUrl("acme")).isEqualTo(API + "acme?mode=json");
        assertThat(connector.apiUrl("  acme-labs  ")).isEqualTo(API + "acme-labs?mode=json");
    }

    @Test
    void a_board_page_becomes_the_postings_endpoint_on_its_own_host() {
        assertThat(connector.apiUrl("https://jobs.lever.co/acme"))
                .isEqualTo(API + "acme?mode=json");
        assertThat(connector.apiUrl("https://jobs.lever.co/acme/abc-123/apply"))
                .isEqualTo(API + "acme?mode=json");
        assertThat(connector.apiUrl("https://jobs.eu.lever.co/acme"))
                .isEqualTo("https://api.eu.lever.co/v0/postings/acme?mode=json");
    }

    @Test
    void an_api_url_keeps_its_query_and_gains_the_json_mode() {
        assertThat(connector.apiUrl(API + "acme")).isEqualTo(API + "acme?mode=json");
        assertThat(connector.apiUrl(API + "acme?limit=100"))
                .isEqualTo(API + "acme?limit=100&mode=json");
        assertThat(connector.apiUrl(API + "acme?mode=json"))
                .isEqualTo(API + "acme?mode=json");
    }

    @Test
    void anything_else_is_refused_with_the_sentence_that_says_what_works() {
        for (String input : new String[] {"", "   ", "https://example.com/acme",
                "https://api.lever.co/v1/postings/acme", "not a token!"}) {
            assertThatThrownBy(() -> connector.apiUrl(input))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessage(LeverConnector.SENTENCE);
        }
    }

    @Test
    void the_connector_names_the_label_a_feed_stores() {
        assertThat(connector.source()).isEqualTo("lever");
    }
}
