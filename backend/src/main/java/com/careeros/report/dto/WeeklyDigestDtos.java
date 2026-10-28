package com.careeros.report.dto;

import com.careeros.report.entity.WeeklyDigest;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

/**
 * The weekly letter's wire shape (roadmap 19.4).
 *
 * <p>{@code weekStart} is a date, not a timestamp: the letter is about a week, and a moment
 * would invite a reader to convert it into their own timezone and land on the Sunday before.
 * The payload is the engine's digest as it was composed -- the same keys the analysis page
 * already reads -- so the browser and the mailer read one shape.
 *
 * <p>The receipt travels with the letter (roadmap 21.3): when it last left ({@code
 * deliveredAt}), the transport's last refusal ({@code deliveryError}, null after a success)
 * and how many attempts it has had ({@code deliveryAttempts}). Zero attempts is "nobody has
 * tried" -- the dashboard's compose -- which is not the same fact as "tried and refused".
 */
public final class WeeklyDigestDtos {

    public record WeeklyDigestDto(
            UUID id,
            LocalDate weekStart,
            int windowDays,
            OffsetDateTime generatedAt,
            Map<String, Object> payload,
            OffsetDateTime deliveredAt,
            String deliveryError,
            int deliveryAttempts) {

        public static WeeklyDigestDto of(WeeklyDigest digest) {
            return new WeeklyDigestDto(digest.getId(), digest.getWeekStart(), digest.getWindowDays(),
                    digest.getGeneratedAt(), digest.getPayload(), digest.getDeliveredAt(),
                    digest.getDeliveryError(), digest.getDeliveryAttempts());
        }
    }

    private WeeklyDigestDtos() {
    }
}
