package com.careeros.auth.dto;

/** Access (JWT, 15m) + opaque refresh (30d, rotated) token pair. */
public record TokenPairResponse(
        String accessToken,
        String refreshToken,
        String tokenType,
        long accessExpiresInSeconds) {

    public static TokenPairResponse of(String accessToken, String refreshToken, long accessExpiresInSeconds) {
        return new TokenPairResponse(accessToken, refreshToken, "Bearer", accessExpiresInSeconds);
    }
}
