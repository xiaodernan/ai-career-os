package com.careeros.auth.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/** All fields optional; null means "leave unchanged". */
public record UpdateMeRequest(
        @Size(min = 1, max = 120) String displayName,
        @Size(max = 240) String headline,
        @Size(max = 120) String location,
        @Size(max = 5000) String summary,
        @DecimalMin("0") @DecimalMax("60") BigDecimal yearsExperience,
        @Size(max = 20) List<@Size(max = 80) String> targetRoles,
        @Size(max = 20) List<@Size(max = 120) String> targetLocations,
        Map<String, Object> links,
        Map<String, Object> workAuthorization,
        Map<String, Object> preferences) {
}
