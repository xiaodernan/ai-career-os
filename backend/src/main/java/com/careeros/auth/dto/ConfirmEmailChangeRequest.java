package com.careeros.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ConfirmEmailChangeRequest(
        @NotBlank @Size(max = 512) String token) {
}
