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

    public static MeResponse of(String displayName, String email, String locale, UserProfile profile) {
        return new MeResponse(displayName, email, locale, profile.getHeadline(), profile.getLocation(),
                profile.getYearsExperience(), profile.getTargetRoles(), profile.getTargetLocations(),
                profile.getLinks(), profile.getWorkAuthorization(), profile.getPreferences());
    }
}
