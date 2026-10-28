package com.careeros.notification.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * The inbox's wire shapes (roadmap 19.3).
 *
 * <p>An item carries the signal it was read from -- a title, a subject, the vocabulary the
 * backend already uses -- and never a rendered sentence: the reader's language is the browser's
 * to know, so the sentence is composed there from {@code kind} and the two names. {@code count}
 * is the number of postings a quiet night proposed, {@code note} the reason a pull failed; each
 * is present only on the kind that has it, and JSON answers null for the other.
 */
public final class NotificationDtos {

    public record NotificationItem(
            String key,
            String kind,
            String title,
            String subject,
            String status,
            Integer count,
            String note,
            String link,
            OffsetDateTime at,
            boolean read) {
    }

    /** The inbox and its unread count, computed together so the two cannot disagree. */
    public record Inbox(List<NotificationItem> items, int unread, OffsetDateTime generatedAt) {
    }

    /** The keys a read request names; keys the inbox is not showing are ignored. */
    public record KeysRequest(
            @NotEmpty @Size(max = 200) List<@NotBlank @Size(max = 160) String> keys) {
    }

    /** One item to file away. */
    public record KeyRequest(@NotBlank @Size(max = 160) String key) {
    }

    private NotificationDtos() {
    }
}
