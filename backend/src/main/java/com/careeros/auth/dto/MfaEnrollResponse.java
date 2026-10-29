package com.careeros.auth.dto;

/**
 * The seed and the URI are two spellings of the same secret, shown once: the browser renders the
 * URI as a QR code and offers the base32 for a phone that cannot scan.
 */
public record MfaEnrollResponse(String secret, String otpauthUri) {
}
