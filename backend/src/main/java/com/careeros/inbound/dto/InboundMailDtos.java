package com.careeros.inbound.dto;

import jakarta.validation.constraints.NotNull;
import java.time.OffsetDateTime;
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
}
