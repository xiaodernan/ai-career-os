package com.careeros.common;

import org.springframework.http.HttpStatus;

/**
 * Stable machine-readable error codes. Never rename an emitted code; add new ones.
 *
 * <p>A code that stops naming anything is removed rather than kept as an empty
 * bucket. {@code BAD_REQUEST} answered with twelve different sentences; the
 * split that gave each of them a code left it naming none, and a name that
 * means nothing is not a contract. Nothing in the browser's table ever
 * answered it, so no reader lost a sentence.
 */
public enum ApiErrorCode {
    VALIDATION_FAILED(HttpStatus.BAD_REQUEST),
    VALIDATION_FIELD_REQUIRED(HttpStatus.BAD_REQUEST),
    VALIDATION_KIND_UNKNOWN(HttpStatus.BAD_REQUEST),
    MALFORMED_REQUEST(HttpStatus.BAD_REQUEST),
    METHOD_NOT_ALLOWED(HttpStatus.METHOD_NOT_ALLOWED),
    FILE_TOO_LARGE(HttpStatus.BAD_REQUEST),
    INVALID_FILE_TYPE(HttpStatus.BAD_REQUEST),
    FILE_EMPTY(HttpStatus.BAD_REQUEST),
    UPLOAD_UNREADABLE(HttpStatus.BAD_REQUEST),
    FILE_KEY_MALFORMED(HttpStatus.BAD_REQUEST),
    FILE_KEY_INVALID(HttpStatus.BAD_REQUEST),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED),
    TOKEN_INVALID(HttpStatus.UNAUTHORIZED),
    TOKEN_MALFORMED(HttpStatus.UNAUTHORIZED),
    TOKEN_OWNER_NOT_FOUND(HttpStatus.UNAUTHORIZED),
    TOKEN_EXPIRED(HttpStatus.UNAUTHORIZED),
    TOKEN_REUSED(HttpStatus.UNAUTHORIZED),
    RESET_TOKEN_INVALID(HttpStatus.BAD_REQUEST),
    RESET_TOKEN_OWNER_NOT_FOUND(HttpStatus.BAD_REQUEST),
    FORBIDDEN(HttpStatus.FORBIDDEN),
    USER_DISABLED(HttpStatus.FORBIDDEN),
    NOT_FOUND(HttpStatus.NOT_FOUND),
    AI_SERVICE_NOT_FOUND(HttpStatus.NOT_FOUND),
    USER_NOT_FOUND(HttpStatus.NOT_FOUND),
    PROFILE_NOT_FOUND(HttpStatus.NOT_FOUND),
    CONTACT_NOT_FOUND(HttpStatus.NOT_FOUND),
    RESUME_NOT_FOUND(HttpStatus.NOT_FOUND),
    RESUME_NOT_AVAILABLE(HttpStatus.NOT_FOUND),
    RESUME_NOT_PARSED(HttpStatus.NOT_FOUND),
    RESUME_NOT_TAILABLE(HttpStatus.NOT_FOUND),
    RESUME_FILE_MISSING(HttpStatus.NOT_FOUND),
    RESUME_NOT_INGESTED(HttpStatus.NOT_FOUND),
    RESUME_TEXT_NOT_READY(HttpStatus.BAD_REQUEST),
    VERSION_NOT_FOUND(HttpStatus.NOT_FOUND),
    VERSION_NOT_OWNED(HttpStatus.NOT_FOUND),
    RESUME_VERSION_MISSING(HttpStatus.NOT_FOUND),
    JOB_NOT_FOUND(HttpStatus.NOT_FOUND),
    SAVED_SEARCH_NOT_FOUND(HttpStatus.NOT_FOUND),
    COMPANY_NOT_FOUND(HttpStatus.NOT_FOUND),
    JD_NOT_FOUND(HttpStatus.NOT_FOUND),
    MATCH_NOT_FOUND(HttpStatus.NOT_FOUND),
    APPLICATION_NOT_FOUND(HttpStatus.NOT_FOUND),
    SESSION_NOT_FOUND(HttpStatus.NOT_FOUND),
    CONVERSATION_NOT_FOUND(HttpStatus.NOT_FOUND),
    INTERVIEW_ALREADY_STARTED(HttpStatus.BAD_REQUEST),
    INTERVIEW_NOT_STARTED(HttpStatus.BAD_REQUEST),
    INTERVIEW_NOTHING_TO_FINALIZE(HttpStatus.BAD_REQUEST),
    INTERVIEW_NO_QUESTION(HttpStatus.BAD_REQUEST),
    NOTE_NOT_FOUND(HttpStatus.NOT_FOUND),
    SOURCE_NOT_FOUND(HttpStatus.NOT_FOUND),
    DOCUMENT_NOT_FOUND(HttpStatus.NOT_FOUND),
    DOCUMENT_KEY_NOT_OWNED(HttpStatus.NOT_FOUND),
    INGESTION_FEED_NOT_FOUND(HttpStatus.NOT_FOUND),
    INGESTION_RUN_NOT_FOUND(HttpStatus.NOT_FOUND),
    /** The run's plan was already written to the board; a second write would duplicate it. */
    INGESTION_RUN_ALREADY_APPLIED(HttpStatus.CONFLICT),
    /** A failed run has no plan, so there is nothing to apply. */
    INGESTION_RUN_NOT_APPLICABLE(HttpStatus.CONFLICT),
    RUN_NOT_FOUND(HttpStatus.NOT_FOUND),
    FEED_URL_INVALID(HttpStatus.BAD_REQUEST),
    /** A board address the connector could not read: token, page address or API URL. */
    FEED_BOARD_INVALID(HttpStatus.BAD_REQUEST),
    FEED_LIMIT_REACHED(HttpStatus.BAD_REQUEST),
    SAVED_SEARCH_EMPTY(HttpStatus.BAD_REQUEST),
    SALARY_RANGE_INVALID(HttpStatus.BAD_REQUEST),
    TAILORED_BODY_MISSING(HttpStatus.BAD_REQUEST),
    INVALID_STATUS(HttpStatus.BAD_REQUEST),
    INVALID_TRANSITION(HttpStatus.BAD_REQUEST),
    BUNDLE_NO_SECTION(HttpStatus.BAD_REQUEST),
    BUNDLE_NOT_PLANNABLE(HttpStatus.BAD_REQUEST),
    EMAIL_ALREADY_REGISTERED(HttpStatus.CONFLICT),
    RATE_LIMITED(HttpStatus.TOO_MANY_REQUESTS),
    AI_SERVICE_BAD_REQUEST(HttpStatus.BAD_REQUEST),
    AI_SERVICE_CONFLICT(HttpStatus.CONFLICT),
    AI_SERVICE_EMPTY_RESPONSE(HttpStatus.BAD_GATEWAY),
    AI_SERVICE_UNAVAILABLE(HttpStatus.BAD_GATEWAY),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR),
    STORAGE_WRITE_FAILED(HttpStatus.INTERNAL_SERVER_ERROR),
    STORAGE_PRESIGN_FAILED(HttpStatus.INTERNAL_SERVER_ERROR),
    STORAGE_DELETE_FAILED(HttpStatus.INTERNAL_SERVER_ERROR),
    STORAGE_READ_FAILED(HttpStatus.INTERNAL_SERVER_ERROR);

    private final HttpStatus status;

    ApiErrorCode(HttpStatus status) {
        this.status = status;
    }

    public HttpStatus status() {
        return status;
    }
}
