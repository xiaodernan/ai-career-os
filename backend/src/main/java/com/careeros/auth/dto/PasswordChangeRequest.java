package com.careeros.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * The two values a signed-in account types to replace its password (roadmap 24.1). The current
 * one is the re-authentication: a stolen open tab must not be enough to lock the owner out.
 */
public record PasswordChangeRequest(
        @NotBlank @Size(max = 72) String currentPassword,
        @NotBlank @Size(min = 8, max = 72) String newPassword) {
}
