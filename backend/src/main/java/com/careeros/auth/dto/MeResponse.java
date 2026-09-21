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
        String headline,
        String location,
        @DecimalMin("0") @DecimalMax("60") BigDecimal yearsExperience,
        List<String> targetRoles,
        List<String> targetLocations,
        Map<String, Object> links,
        Map<String, Object> workAuthorization,
        Map<String, Object> preferences) {

    public static MeResponse of(String displayName, String email, UserProfile profile) {
        return new MeResponse(displayName, email, profile.getHeadline(), profile.getLocation(),
                profile.getYearsExperience(), profile.getTargetRoles(), profile.getTargetLocations(),
                profile.getLinks(), profile.getWorkAuthorization(), profile.getPreferences());
    }
}
