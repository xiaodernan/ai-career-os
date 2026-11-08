package com.careeros.network.dto;

import com.careeros.network.entity.Contact;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.UUID;

/**
 * The registry's wire shapes. One record per direction, kept total: the browser sends
 * `ContactRequest` and reads `ContactItem`, and nothing between them invents a third
 * spelling. `lastTouchAt` is the client's claim about when contact last happened — the
 * server does not guess it from request arrival, because "I talked to her yesterday"
 * and "I am logging this today" are different sentences.
 */
public final class ContactDtos {

    public record ContactRequest(
            @NotBlank @Size(max = 200) String name,
            @Size(max = 200) String role,
            @Size(max = 200) String company,
            @Size(max = 80) String relation,
            @Size(max = 320) String email,
            String notes,
            OffsetDateTime lastTouchAt) {
    }

    public record ContactItem(
            UUID id,
            String name,
            String role,
            String company,
            String relation,
            String email,
            String notes,
            OffsetDateTime lastTouchAt,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt) {

        public static ContactItem of(Contact c) {
            return new ContactItem(c.getId(), c.getName(), c.getRole(), c.getCompany(),
                    c.getRelation(), c.getEmail(), c.getNotes(), c.getLastTouchAt(),
                    c.getCreatedAt(), c.getUpdatedAt());
        }
    }

    /** One relation the reader's own contacts carry, and how many rows sit behind it (80). */
    public record RelationCount(String relation, long count) {

        public static RelationCount of(Object[] row) {
            return new RelationCount((String) row[0], ((Number) row[1]).longValue());
        }
    }

    private ContactDtos() {
    }
}
