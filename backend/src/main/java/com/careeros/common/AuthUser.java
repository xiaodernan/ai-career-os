package com.careeros.common;

import java.util.UUID;

/**
 * Authenticated principal placed in the SecurityContext by JwtAuthFilter.
 *
 * <p>{@code familyId} is the refresh-token family the access token was minted with. It is
 * nullable on purpose: tokens issued before the claim existed, and the principals tests
 * hand-build, carry no family, and every reader of it treats null as "the asking device is
 * not known" rather than refusing the call.
 */
public record AuthUser(UUID id, String email, String role, UUID familyId) {

    public AuthUser(UUID id, String email, String role) {
        this(id, email, role, null);
    }
}
