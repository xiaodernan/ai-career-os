package com.careeros.ai.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Size;

/**
 * What a correction may change. Either field, not both: a wrong fact needs its text fixed,
 * while a fact the user is tired of being reminded about only needs its weight lowered, and
 * requiring both would make the second caller invent new content.
 */
public record UpdateMemoryRequest(
        @Size(max = 4000, message = "memory must stay under 4000 characters")
        String content,

        @DecimalMin(value = "0.0", message = "importance must be between 0 and 1")
        @DecimalMax(value = "1.0", message = "importance must be between 0 and 1")
        Double importance) {
}
