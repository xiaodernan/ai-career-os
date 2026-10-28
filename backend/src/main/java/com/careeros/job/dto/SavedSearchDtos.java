package com.careeros.job.dto;

import com.careeros.job.entity.SavedSearch;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * The saved-search wire shapes (roadmap 19.1).
 *
 * <p>The criterion names are the job board's own query parameters -- `q`, `skills`,
 * `location`, `remote`, `company`, `minSalary`, `maxSalary` -- so a saved search is a
 * question the board already knows how to answer, not a second vocabulary that the
 * alert path would have to translate back. `sort`, `page` and `size` are left out on
 * purpose: they describe how an answer is shown, not what is being asked.
 */
public final class SavedSearchDtos {

    public record Criteria(
            @Size(max = 200) String q,
            @Size(max = 200) String location,
            @Size(max = 200) String company,
            Boolean remote,
            @Min(0) Integer minSalary,
            @Min(0) Integer maxSalary,
            @Size(max = 20) List<@NotBlank @Size(max = 60) String> skills) {

        /** The stored map as this shape, with absent keys as null. */
        public static Criteria of(Map<String, Object> stored) {
            if (stored == null) {
                return new Criteria(null, null, null, null, null, null, null);
            }
            return new Criteria(
                    text(stored.get("q")),
                    text(stored.get("location")),
                    text(stored.get("company")),
                    stored.get("remote") instanceof Boolean remote ? remote : null,
                    integer(stored.get("minSalary")),
                    integer(stored.get("maxSalary")),
                    strings(stored.get("skills")));
        }

        private static String text(Object value) {
            return value instanceof String s ? s : null;
        }

        private static Integer integer(Object value) {
            return value instanceof Number n ? n.intValue() : null;
        }

        private static List<String> strings(Object value) {
            if (!(value instanceof List<?> raw)) {
                return null;
            }
            return raw.stream().filter(String.class::isInstance).map(String.class::cast).toList();
        }
    }

    public record SavedSearchRequest(
            @NotBlank @Size(max = 80) String name,
            @NotNull @Valid Criteria criteria) {
    }

    public record SavedSearchItem(
            UUID id,
            String name,
            Criteria criteria,
            OffsetDateTime createdAt) {

        public static SavedSearchItem of(SavedSearch saved) {
            return new SavedSearchItem(saved.getId(), saved.getName(),
                    Criteria.of(saved.getCriteria()), saved.getCreatedAt());
        }
    }

    private SavedSearchDtos() {
    }
}
