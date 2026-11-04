package com.careeros.auth.dto;

import com.careeros.auth.entity.UserProfile;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/** Display info + preferences exposed on GET/PATCH /api/v1/me. */
public record MeResponse(
        String displayName,
        String email,
        /**
         * `users.role` — the schema's own two words, "user" or "admin". The settings page's
         * account badge draws it; the response used to omit it, so the badge could only ever
         * fall back to "user" and an admin read as the default account on their own page.
         * Login already answers this field on `AuthUserResponse`; this is the same row.
         */
        String role,
        /**
         * The account's language (roadmap 21.4): "en" or "zh". The browser reads its own copy
         * from the cookie for the first paint; this is the copy a browser with no choice yet
         * adopts, and the copy the nightly letter is written in.
         */
        String locale,
        String headline,
        String location,
        @DecimalMin("0") @DecimalMax("60") BigDecimal yearsExperience,
        List<String> targetRoles,
        List<String> targetLocations,
        Map<String, Object> links,
        Map<String, Object> workAuthorization,
        Map<String, Object> preferences) {

    public static MeResponse of(String displayName, String email, String role, String locale, UserProfile profile) {
        return new MeResponse(displayName, email, role, locale, profile.getHeadline(), profile.getLocation(),
                profile.getYearsExperience(), profile.getTargetRoles(), profile.getTargetLocations(),
                profile.getLinks(), profile.getWorkAuthorization(), profile.getPreferences());
    }
}
