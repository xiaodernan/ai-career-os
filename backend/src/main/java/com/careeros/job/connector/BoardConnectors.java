package com.careeros.job.connector;

import java.util.List;
import java.util.Locale;
import java.util.Optional;
import org.springframework.stereotype.Component;

/**
 * The board connectors a feed's {@code source} can name (roadmap 19.8).
 *
 * <p>A label that matches no connector is the generic feed — a URL the reader supplies
 * as-is — so this registry never refuses a feed; it only decides whether one of the
 * board connectors owns the address.
 */
@Component
public class BoardConnectors {

    private final List<BoardConnector> all;

    public BoardConnectors(List<BoardConnector> all) {
        this.all = List.copyOf(all);
    }

    /** The connector named by {@code source}, case-insensitively; empty for anything else. */
    public Optional<BoardConnector> forSource(String source) {
        if (source == null || source.isBlank()) {
            return Optional.empty();
        }
        String wanted = source.trim().toLowerCase(Locale.ROOT);
        return all.stream()
                .filter(connector -> connector.source().toLowerCase(Locale.ROOT).equals(wanted))
                .findFirst();
    }
}
