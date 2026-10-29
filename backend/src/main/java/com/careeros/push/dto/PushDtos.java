package com.careeros.push.dto;

import com.careeros.push.entity.PushSubscription;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * The push-subscription wire shapes (roadmap 33.1).
 *
 * <p>The request is the browser's own {@code PushSubscription.toJSON()} with an optional label:
 * the endpoint, the {@code p256dh} and {@code auth} keys. The answer names the row and when it
 * was first kept -- not the keys back, which the browser already holds and a list endpoint has no
 * reason to repeat.
 */
public final class PushDtos {

    private PushDtos() {
    }

    public record PushSubscriptionRequest(
            @NotBlank @Size(max = 2048) String endpoint,
            @NotBlank @Size(max = 200) String p256dh,
            @NotBlank @Size(max = 100) String auth,
            @Size(max = 120) String label) {
    }

    public record PushSubscriptionItem(
            UUID id,
            String endpoint,
            String label,
            OffsetDateTime createdAt) {

        public static PushSubscriptionItem of(PushSubscription row) {
            return new PushSubscriptionItem(row.getId(), row.getEndpointUrl(), row.getLabel(),
                    row.getCreatedAt());
        }
    }
}
