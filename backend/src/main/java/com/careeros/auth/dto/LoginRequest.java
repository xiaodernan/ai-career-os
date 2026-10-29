package com.careeros.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * A sign-in. The optional {@code code} is the account's second factor (roadmap 36.2): six digits
 * from the authenticator app, or one of the printed recovery codes. It is optional because the
 * account may have no second factor -- the login page cannot know before it asks, and sending no
 * code to an enrolled account is answered {@code MFA_REQUIRED}, which is the browser's cue to
 * show the field. Length is the only shape checked here: the spelling of a recovery code (hyphens,
 * case, surrounding spaces) is normalized where it is verified, and six digits versus sixteen
 * printed characters is a decision the service makes with the stored seed and hashes in hand.
 */
public record LoginRequest(
        @NotBlank @Email @Size(max = 255) String email,
        @NotBlank @Size(max = 72) String password,
        @Size(max = 32) String code) {
}
