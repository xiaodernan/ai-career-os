package com.careeros.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * The two values an account types to erase itself (roadmap 24.2): the password proves who is
 * asking, and the typed email makes the request a second, explicit act -- the account's
 * address is on the screen anyway, so this is not a secret, but it cannot be produced by a
 * mis-click on the destructive button.
 */
public record EraseAccountRequest(
        @NotBlank @Size(max = 72) String password,
        @NotBlank @Size(max = 255) String confirmEmail) {
}
