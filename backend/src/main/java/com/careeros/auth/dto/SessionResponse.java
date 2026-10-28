package com.careeros.auth.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * One signed-in device: a refresh-token family folded into what the reader needs to
 * recognise the door. {@code id} is the family id; {@code startedAt} is when the first
 * token of the family was issued, {@code lastSeenAt} the most recent rotation, and
 * {@code expiresAt} the furthest any live token reaches.
 */
public record SessionResponse(
        UUID id,
        String userAgent,
        String clientIp,
        OffsetDateTime startedAt,
        OffsetDateTime lastSeenAt,
        OffsetDateTime expiresAt) {
}
