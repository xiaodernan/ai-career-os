package com.careeros.job.connector;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Which label names which board (roadmap 19.8). A blank or unknown label is the generic
 * feed -- a URL the reader supplies as-is -- so the registry never refuses a feed; it
 * only decides whether one of the board connectors owns the address.
 */
class BoardConnectorsTest {

    private final BoardConnectors connectors = new BoardConnectors(
            List.of(new GreenhouseConnector(), new LeverConnector()));

    @Test
    void a_label_names_its_connector_case_insensitively() {
        assertThat(connectors.forSource(" Greenhouse ").orElseThrow().source())
                .isEqualTo("greenhouse");
        assertThat(connectors.forSource("LEVER").orElseThrow().source()).isEqualTo("lever");
    }

    @Test
    void a_blank_or_unknown_label_is_the_generic_feed() {
        assertThat(connectors.forSource(null)).isEmpty();
        assertThat(connectors.forSource("  ")).isEmpty();
        assertThat(connectors.forSource("rss")).isEmpty();
    }
}
