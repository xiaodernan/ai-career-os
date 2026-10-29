package com.careeros.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

/**
 * The proof that turns the second factor on: the account's current password, so a stolen
 * session cannot bolt a phone onto the account and outlive a password change, and a code from
 * the authenticator, so the seed the enrollment answered is really held by the reader.
 */
public record MfaActivateRequest(
        @NotBlank String password,
        @NotBlank @Pattern(regexp = "\\d{6}", message = "must be six digits") String code) {
}
