package com.careeros.common;

import java.util.List;
import java.util.Map;

/** Domain/security exception carrying a stable error code; rendered by GlobalExceptionHandler. */
public class ApiException extends RuntimeException {

    private final ApiErrorCode code;
    private final List<Map<String, Object>> details;

    public ApiException(ApiErrorCode code, String message) {
        this(code, message, List.of());
    }

    public ApiException(ApiErrorCode code, String message, List<Map<String, Object>> details) {
        super(message, null, true, false);
        this.code = code;
        this.details = details == null ? List.of() : List.copyOf(details);
    }

    public ApiErrorCode code() {
        return code;
    }

    public List<Map<String, Object>> details() {
        return details;
    }

    @Override
    public String getMessage() {
        return super.getMessage();
    }
}
