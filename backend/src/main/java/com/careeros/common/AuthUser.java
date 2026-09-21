package com.careeros.common;

import java.util.UUID;

/** Authenticated principal placed in the SecurityContext by JwtAuthFilter. */
public record AuthUser(UUID id, String email, String role) {
}
