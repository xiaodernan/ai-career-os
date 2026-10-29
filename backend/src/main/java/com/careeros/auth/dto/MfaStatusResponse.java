package com.careeros.auth.dto;

/**
 * {@code enabled} is the second factor being in force; {@code pending} is an enrollment the
 * reader started and has not yet proven with a code from the phone; {@code recoveryCodesRemaining}
 * is how many printed codes can still answer, which the settings card reads as "3 left".
 */
public record MfaStatusResponse(boolean enabled, boolean pending, long recoveryCodesRemaining) {
}
