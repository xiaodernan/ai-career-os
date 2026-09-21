package com.careeros.common;

import org.springframework.http.HttpStatus;

/** Stable machine-readable error codes. Never rename an emitted code; add new ones. */
public enum ApiErrorCode {
    VALIDATION_FAILED(HttpStatus.BAD_REQUEST),
    MALFORMED_REQUEST(HttpStatus.BAD_REQUEST),
    BAD_REQUEST(HttpStatus.BAD_REQUEST),
    FILE_TOO_LARGE(HttpStatus.BAD_REQUEST),
    INVALID_FILE_TYPE(HttpStatus.BAD_REQUEST),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED),
    TOKEN_INVALID(HttpStatus.UNAUTHORIZED),
    TOKEN_EXPIRED(HttpStatus.UNAUTHORIZED),
    TOKEN_REUSED(HttpStatus.UNAUTHORIZED),
    RESET_TOKEN_INVALID(HttpStatus.BAD_REQUEST),
    FORBIDDEN(HttpStatus.FORBIDDEN),
    USER_DISABLED(HttpStatus.FORBIDDEN),
    NOT_FOUND(HttpStatus.NOT_FOUND),
    EMAIL_ALREADY_REGISTERED(HttpStatus.CONFLICT),
    RATE_LIMITED(HttpStatus.TOO_MANY_REQUESTS),
    AI_SERVICE_ERROR(HttpStatus.BAD_GATEWAY),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR);

    private final HttpStatus status;

    ApiErrorCode(HttpStatus status) {
        this.status = status;
    }

    public HttpStatus status() {
        return status;
    }
}
