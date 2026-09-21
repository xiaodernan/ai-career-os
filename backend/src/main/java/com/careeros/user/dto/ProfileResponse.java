package com.careeros.user.dto;

import com.careeros.auth.entity.UserProfile;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Full user_profiles row exposed on GET/PATCH /api/v1/users/me/profile. */
public record ProfileResponse(
        UUID id,
        UUID userId,
        String headline,
        String summary,
        String location,
        BigDecimal yearsExperience,
        List<String> targetRoles,
        List<String> targetLocations,
        Map<String, Object> links,
        Map<String, Object> workAuthorization,
        Map<String, Object> preferences) {

    public static ProfileResponse from(UserProfile p) {
        return new ProfileResponse(p.getId(), p.getUserId(), p.getHeadline(), p.getSummary(),
                p.getLocation(), p.getYearsExperience(), p.getTargetRoles(), p.getTargetLocations(),
                p.getLinks(), p.getWorkAuthorization(), p.getPreferences());
    }
}
