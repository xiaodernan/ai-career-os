package com.careeros.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * A request to move the login address. The password is the re-authentication: a borrowed
 * tab, even one holding a valid session, cannot start the move. The new address is where
 * the confirmation letter goes -- nothing changes until that mailbox answers.
 */
public record EmailChangeRequest(
        @NotBlank @Size(max = 72) String password,
        @NotBlank @Email @Size(max = 255) String newEmail) {
}
