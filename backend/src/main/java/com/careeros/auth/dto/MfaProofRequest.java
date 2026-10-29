package com.careeros.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * The proof that reprints the recovery codes or turns the second factor off (roadmap 36.3):
 * the account's current password, and either a six-digit code from the authenticator or one of
 * the printed recovery codes -- which is why the ceiling is wider than activation's six digits,
 * whose field never accepts a recovery code.
 */
public record MfaProofRequest(
        @NotBlank String password,
        @NotBlank @Size(max = 64) String code) {
}
