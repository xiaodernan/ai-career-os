package com.careeros.auth.dto;

/**
 * {@code enabled} is the second factor being in force; {@code pending} is an enrollment the
 * reader started and has not yet proven with a code from the phone.
 */
public record MfaStatusResponse(boolean enabled, boolean pending) {
}
