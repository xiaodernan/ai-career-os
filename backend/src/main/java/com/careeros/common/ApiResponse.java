package com.careeros.common;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * Unified response envelope: {"success":true,"data":…,"error":null} /
 * {"success":false,"data":null,"error":{code,message,details[]}}.
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public record ApiResponse<T>(boolean success, T data, ApiError error) {

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, data, null);
    }

    public static <T> ApiResponse<T> error(ApiError error) {
        return new ApiResponse<>(false, null, error);
    }

    public static <T> ApiResponse<T> error(ApiErrorCode code, String message) {
        return new ApiResponse<>(false, null, ApiError.of(code, message));
    }
}
