package com.careeros.job.connector;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

/**
 * The addresses a Greenhouse board is known by (roadmap 19.8), and the ones it is not:
 * a token, a public board page (both hosts Greenhouse serves it from), or the API URL.
 * The API URL keeps its own query and gains {@code content=true} when it names none,
 * because that parameter is what makes the payload carry each posting's description.
 */
class GreenhouseConnectorTest {

    private static final String API = "https://boards-api.greenhouse.io/v1/boards/";
    private final GreenhouseConnector connector = new GreenhouseConnector();

    @Test
    void a_token_becomes_the_jobs_endpoint() {
        assertThat(connector.apiUrl("acme")).isEqualTo(API + "acme/jobs?content=true");
        assertThat(connector.apiUrl("  acme_labs-2  "))
                .isEqualTo(API + "acme_labs-2/jobs?content=true");
    }

    @Test
    void a_board_page_becomes_the_jobs_endpoint() {
        assertThat(connector.apiUrl("https://boards.greenhouse.io/acme"))
                .isEqualTo(API + "acme/jobs?content=true");
        assertThat(connector.apiUrl("https://job-boards.greenhouse.io/acme/jobs/4001"))
                .isEqualTo(API + "acme/jobs?content=true");
    }

    @Test
    void an_api_url_keeps_its_query_and_gains_the_content_parameter() {
        assertThat(connector.apiUrl(API + "acme/jobs"))
                .isEqualTo(API + "acme/jobs?content=true");
        assertThat(connector.apiUrl(API + "acme/jobs?per_page=100"))
                .isEqualTo(API + "acme/jobs?per_page=100&content=true");
        assertThat(connector.apiUrl(API + "acme/jobs?content=true"))
                .isEqualTo(API + "acme/jobs?content=true");
    }

    @Test
    void anything_else_is_refused_with_the_sentence_that_says_what_works() {
        for (String input : new String[] {"", "   ", "https://example.com/acme",
                "https://boards-api.greenhouse.io/other/acme", "not a token!"}) {
            assertThatThrownBy(() -> connector.apiUrl(input))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessage(GreenhouseConnector.SENTENCE);
        }
    }

    @Test
    void the_connector_names_the_label_a_feed_stores() {
        assertThat(connector.source()).isEqualTo("greenhouse");
    }
}
