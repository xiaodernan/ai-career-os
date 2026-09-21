package com.careeros.auth.dto;

public record AuthResponse(AuthUserResponse user, TokenPairResponse tokens) {
}
