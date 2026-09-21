package com.careeros.common;

import java.util.List;
import java.util.Map;

/** Structured error payload: {code, message, details[]}. */
public record ApiError(String code, String message, List<Map<String, Object>> details) {

    public static ApiError of(ApiErrorCode code, String message) {
        return new ApiError(code.name(), message, List.of());
    }

    public static ApiError of(ApiErrorCode code, String message, List<Map<String, Object>> details) {
        return new ApiError(code.name(), message, details == null ? List.of() : List.copyOf(details));
    }
}
