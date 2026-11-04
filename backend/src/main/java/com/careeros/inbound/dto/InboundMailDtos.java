package com.careeros.inbound.dto;

import jakarta.validation.constraints.NotNull;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * The replies page's wire shapes (roadmap 37.3).
 *
 * <p>A letter carries what it said and what the platform made of it: the reader's own three
 * fields, the engine's reading (null while the classifier has not answered), the stage that
 * reading suggests, and the application the letter is filed on. The suggestion is a stage
 * name from the board's own vocabulary, not a decision -- applying it is a separate, explicit
 * write to the application.
 */
public final class InboundMailDtos {

    private InboundMailDtos() {
    }

    public record InboundMailItem(UUID id, String fromAddress, String subject, String bodyText,
                                  String intent, String company, String role,
                                  String suggestedStage, UUID applicationId, String applicationTitle,
                                  OffsetDateTime receivedAt, OffsetDateTime filedAt) {
    }

    /** The one thing a reader chooses when filing a letter by hand. */
    public record FileRequest(@NotNull(message = "applicationId is required") UUID applicationId) {
    }

    /** One chip's number: a reading's word, or `unread` for the letters it has not read. */
    public record IntentCount(String intent, long count) {
    }

    /**
     * The whole row of chips (49.4), in the order the page draws them. Every reading is
     * present, zeros included, so the page never has to invent a number for a word.
     *
     * <p>{@code unfiled} is the number on the waiting switch (49.5): how many of the letters
     * under the same words still wait for a card. It is answered whether the switch is on or
     * off, because it is the switch's own label -- with it on, {@code items} describe exactly
     * that pile, so the six add up to it.
     */
    public record IntentCounts(List<IntentCount> items, long unfiled) {
    }
}
