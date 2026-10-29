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
    /** Signing in was refused: the pair the reader typed opens no account. */
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED),
    /**
     * A signed-in reader typed the wrong current password for a re-authenticated act -- changing
     * the password, moving the address, erasing the account. Not {@code INVALID_CREDENTIALS}:
     * this reader is signed in with a working password, so the sentence says the one typed is
     * wrong rather than telling them their account does not exist.
     */
    CURRENT_PASSWORD_INCORRECT(HttpStatus.UNAUTHORIZED),
    /** The new password is the one already on the account, so the change would buy nothing. */
    PASSWORD_UNCHANGED(HttpStatus.BAD_REQUEST),
    /** Two-factor is already on: a second enrollment would mint a second seed for one account. */
    MFA_ALREADY_ACTIVE(HttpStatus.CONFLICT),
    /** Activation arrived with no enrollment to prove: there is no seed this code could answer for. */
    MFA_NOT_ENROLLED(HttpStatus.BAD_REQUEST),
    /**
     * The six-digit code is not this seed's code in the accepted window -- mistyped, from a
     * clock too far off, or a code the account already spent (the replay guard refuses the
     * step, and the sentence is the same because the reader's answer is the same: read the
     * phone's current number again).
     */
    MFA_CODE_INVALID(HttpStatus.UNAUTHORIZED),
    /** The typed email is not this account's: the deliberate half of an erasure did not happen. */
    CONFIRMATION_MISMATCH(HttpStatus.BAD_REQUEST),
    TOKEN_INVALID(HttpStatus.UNAUTHORIZED),
    TOKEN_MALFORMED(HttpStatus.UNAUTHORIZED),
    TOKEN_OWNER_NOT_FOUND(HttpStatus.UNAUTHORIZED),
    TOKEN_EXPIRED(HttpStatus.UNAUTHORIZED),
    TOKEN_REUSED(HttpStatus.UNAUTHORIZED),
    RESET_TOKEN_INVALID(HttpStatus.BAD_REQUEST),
    RESET_TOKEN_OWNER_NOT_FOUND(HttpStatus.BAD_REQUEST),
    FORBIDDEN(HttpStatus.FORBIDDEN),
    USER_DISABLED(HttpStatus.FORBIDDEN),
    /** Nothing is served at this address: the route catch-all, and nothing else. */
    NOT_FOUND(HttpStatus.NOT_FOUND),
    /**
     * The login session a reader asked to close is not among their live families -- already
     * closed, or never theirs. Separate from {@code NOT_FOUND}, whose sentence is about an
     * address: this one is about a session, and the reader's answer is to refresh the list.
     */
    LOGIN_SESSION_NOT_FOUND(HttpStatus.NOT_FOUND),
    /**
     * The mail-settings link is unreadable, signed for another account, names an unknown list,
     * or belongs to a deleted account. One answer for all four, so the open internet cannot
     * grade its guesses -- and its own code rather than the catch-all, because the sentence is
     * about a letter's link, not an address.
     */
    MAIL_LINK_INVALID(HttpStatus.NOT_FOUND),
    /**
     * The calendar feed's token is unreadable, signed with a retired secret, a mail link's token
     * rather than this purpose's, or names an account that no longer exists. One answer for all
     * four: a calendar client handed a retired URL stops polling, and the open internet cannot
     * grade its guesses. Its own code because the sentence is about a subscription URL, not an
     * address.
     */
    CALENDAR_LINK_INVALID(HttpStatus.NOT_FOUND),
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
    /** A nightly report says passed or failed; any other ending is not a night's outcome. */
    NIGHTLY_REPORT_STATUS_INVALID(HttpStatus.BAD_REQUEST),
    /** The night's clock ran backwards: a report cannot finish before it started. */
    NIGHTLY_REPORT_CLOCK_REVERSED(HttpStatus.BAD_REQUEST),
    /** A report's summary carries more top-level entries than the column is built to hold. */
    NIGHTLY_REPORT_SUMMARY_TOO_LARGE(HttpStatus.BAD_REQUEST),
    RUN_NOT_FOUND(HttpStatus.NOT_FOUND),
    FEED_URL_INVALID(HttpStatus.BAD_REQUEST),
    /** A board address the connector could not read: token, page address or API URL. */
    FEED_BOARD_INVALID(HttpStatus.BAD_REQUEST),
    FEED_LIMIT_REACHED(HttpStatus.BAD_REQUEST),
    SAVED_SEARCH_EMPTY(HttpStatus.BAD_REQUEST),
    /** The account already keeps as many saved searches as the read path will carry. */
    SAVED_SEARCH_LIMIT_REACHED(HttpStatus.BAD_REQUEST),
    SALARY_RANGE_INVALID(HttpStatus.BAD_REQUEST),
    TAILORED_BODY_MISSING(HttpStatus.BAD_REQUEST),
    INVALID_STATUS(HttpStatus.BAD_REQUEST),
    INVALID_TRANSITION(HttpStatus.BAD_REQUEST),
    BUNDLE_NO_SECTION(HttpStatus.BAD_REQUEST),
    BUNDLE_NOT_PLANNABLE(HttpStatus.BAD_REQUEST),
    EMAIL_ALREADY_REGISTERED(HttpStatus.CONFLICT),
    /** The requested address is the account's current one, so the move would buy nothing. */
    EMAIL_UNCHANGED(HttpStatus.BAD_REQUEST),
    /** The email-change link is unknown, spent or past its window; nothing moved. */
    EMAIL_CHANGE_INVALID(HttpStatus.BAD_REQUEST),
    /** A browser handed over a push address or key this service cannot wake. */
    PUSH_SUBSCRIPTION_INVALID(HttpStatus.BAD_REQUEST),
    /** The account already keeps as many browser registrations as the morning ring will walk. */
    PUSH_SUBSCRIPTION_LIMIT_REACHED(HttpStatus.BAD_REQUEST),
    /** The registration is not among the caller's; already forgotten, or never theirs. */
    PUSH_SUBSCRIPTION_NOT_FOUND(HttpStatus.NOT_FOUND),
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
