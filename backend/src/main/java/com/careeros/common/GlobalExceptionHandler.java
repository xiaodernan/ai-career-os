package com.careeros.common;

import jakarta.validation.ConstraintViolationException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageConversionException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.http.converter.HttpMessageNotWritableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiResponse<Void>> api(ApiException ex) {
        return ResponseEntity.status(ex.code().status())
                .body(ApiResponse.error(ApiError.of(ex.code(), ex.getMessage(), ex.details())));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> validation(MethodArgumentNotValidException ex) {
        List<Map<String, Object>> details = ex.getBindingResult().getFieldErrors().stream()
                .map(GlobalExceptionHandler::fieldDetail)
                .toList();
        return badRequest(ApiErrorCode.VALIDATION_FAILED, "Request validation failed", details);
    }

    @ExceptionHandler(HandlerMethodValidationException.class)
    public ResponseEntity<ApiResponse<Void>> paramValidation(HandlerMethodValidationException ex) {
        List<Map<String, Object>> details = ex.getAllValidationResults().stream()
                .flatMap(r -> r.getResolvableErrors().stream()
                        .map(e -> Map.<String, Object>of("message",
                                e.getDefaultMessage() == null ? "invalid value" : e.getDefaultMessage())))
                .toList();
        return badRequest(ApiErrorCode.VALIDATION_FAILED, "Request validation failed", details);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ApiResponse<Void>> constraint(ConstraintViolationException ex) {
        List<Map<String, Object>> details = ex.getConstraintViolations().stream()
                .map(v -> Map.<String, Object>of("field", String.valueOf(v.getPropertyPath()),
                        "message", v.getMessage()))
                .toList();
        return badRequest(ApiErrorCode.VALIDATION_FAILED, "Request validation failed", details);
    }

    @ExceptionHandler({HttpMessageNotReadableException.class, MissingServletRequestParameterException.class,
            MethodArgumentTypeMismatchException.class})
    public ResponseEntity<ApiResponse<Void>> unreadable(Exception ex) {
        return badRequest(ApiErrorCode.MALFORMED_REQUEST, "Malformed request body or parameters", List.of());
    }

    /**
     * Jackson reports a body whose shape it cannot bind at all — a constructor property filled
     * twice, which is what a client asking for one field under both its name and its alias does
     * to a record — as its superclass {@code HttpMessageConversionException}, not the
     * {@code HttpMessageNotReadableException} mapped above. Without this the caller's malformed
     * request surfaced as a 500 with a stack trace, i.e. as our bug.
     */
    @ExceptionHandler(HttpMessageConversionException.class)
    public ResponseEntity<ApiResponse<Void>> conversion(HttpMessageConversionException ex) {
        if (ex instanceof HttpMessageNotWritableException) {
            return fallback(ex); // our serializer failed; blaming the caller would hide that
        }
        return badRequest(ApiErrorCode.MALFORMED_REQUEST, "Malformed request body or parameters", List.of());
    }

    @ExceptionHandler(AuthenticationException.class)
    public ResponseEntity<ApiResponse<Void>> authentication(AuthenticationException ex) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ApiResponse.error(ApiError.of(ApiErrorCode.UNAUTHORIZED, "Authentication required")));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ApiResponse<Void>> accessDenied(AccessDeniedException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(ApiResponse.error(ApiError.of(ApiErrorCode.FORBIDDEN, "Access denied")));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ApiResponse<Void>> notFound(NoResourceFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ApiResponse.error(ApiError.of(ApiErrorCode.NOT_FOUND, "Resource not found")));
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ApiResponse<Void>> methodNotSupported(HttpRequestMethodNotSupportedException ex) {
        return ResponseEntity.status(HttpStatus.METHOD_NOT_ALLOWED)
                .body(ApiResponse.error(ApiError.of(ApiErrorCode.METHOD_NOT_ALLOWED, "Method not allowed")));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> fallback(Exception ex) {
        log.error("Unhandled exception", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error(ApiError.of(ApiErrorCode.INTERNAL_ERROR, "Internal server error")));
    }

    private static ResponseEntity<ApiResponse<Void>> badRequest(ApiErrorCode code, String message,
                                                                List<Map<String, Object>> details) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                .body(ApiResponse.error(ApiError.of(code, message, details)));
    }

    private static Map<String, Object> fieldDetail(FieldError error) {
        Map<String, Object> detail = new LinkedHashMap<>();
        detail.put("field", error.getField());
        detail.put("message", error.getDefaultMessage());
        detail.put("rejectedValue", error.getRejectedValue());
        return detail;
    }
}
