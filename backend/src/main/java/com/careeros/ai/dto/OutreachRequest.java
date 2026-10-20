package com.careeros.ai.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.Map;

/**
 * The outreach request (Epic 11.2).
 *
 * <p>The outreach generator drafts a message for a real person, so the contact's
 * own fields are the request: the name, the role, the company and what the
 * message is for. The optionals carry the context the draft should use — the
 * resume version it cites from, and any note the user wrote.
 */
public record OutreachRequest(
        @NotBlank @Size(min = 1, max = 200) String name,
        @Size(max = 200) String role,
        @Size(max = 200) String company,
        @Size(max = 40) String purpose,
        @Size(max = 2000) String context,
        String resumeVersionId) {
}
