package com.careeros.job.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.job.dto.SavedSearchDtos.Criteria;
import com.careeros.job.dto.SavedSearchDtos.SavedSearchItem;
import com.careeros.job.dto.SavedSearchDtos.SavedSearchRequest;
import com.careeros.job.entity.SavedSearch;
import com.careeros.job.repository.SavedSearchRepository;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The saved searches a user keeps (roadmap 19.1).
 *
 * <p>The criteria are written as one canonical map: trimmed, blanks dropped, an
 * exactly repeated skill folded to its first occurrence, and `remote=false`
 * left out because the board's switch means "remote only", not "on-site only".
 * Skill case is kept as typed, because the board's own skill filter matches the
 * stored array exactly and "Java" is not the filter "java". Two
 * spellings of the same search therefore store the same row's worth of
 * meaning, which is what lets the nightly sweep (19.2) ask the stored question
 * without re-learning the browser's habits.
 */
@Service
public class SavedSearchService {

    private final SavedSearchRepository savedSearches;

    public SavedSearchService(SavedSearchRepository savedSearches) {
        this.savedSearches = savedSearches;
    }

    @Transactional(readOnly = true)
    public List<SavedSearchItem> list(UUID userId) {
        return savedSearches.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(SavedSearchItem::of)
                .toList();
    }

    @Transactional
    public SavedSearchItem create(UUID userId, SavedSearchRequest request) {
        Map<String, Object> criteria = canonical(request.criteria());
        if (criteria.isEmpty()) {
            throw new ApiException(ApiErrorCode.VALIDATION_STRUCTURE_INVALID,
                    "A saved search needs at least one criterion");
        }
        SavedSearch saved = new SavedSearch();
        saved.setUserId(userId);
        saved.setName(request.name().trim());
        saved.setCriteria(criteria);
        return SavedSearchItem.of(savedSearches.save(saved));
    }

    @Transactional
    public void delete(UUID userId, UUID id) {
        savedSearches.delete(savedSearches.findByIdAndUserId(id, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.SAVED_SEARCH_NOT_FOUND,
                        "Saved search not found")));
    }

    private static Map<String, Object> canonical(Criteria criteria) {
        Map<String, Object> out = new LinkedHashMap<>();
        putText(out, "q", criteria.q());
        putText(out, "location", criteria.location());
        putText(out, "company", criteria.company());
        if (Boolean.TRUE.equals(criteria.remote())) {
            out.put("remote", true);
        }
        Integer min = criteria.minSalary();
        Integer max = criteria.maxSalary();
        if (min != null && max != null && min > max) {
            throw new ApiException(ApiErrorCode.VALIDATION_STRUCTURE_INVALID,
                    "The salary floor is above the salary ceiling");
        }
        if (min != null) {
            out.put("minSalary", min);
        }
        if (max != null) {
            out.put("maxSalary", max);
        }
        if (criteria.skills() != null) {
            List<String> skills = criteria.skills().stream()
                    .map(String::trim)
                    .filter(skill -> !skill.isEmpty())
                    .distinct()
                    .toList();
            if (!skills.isEmpty()) {
                out.put("skills", skills);
            }
        }
        return out;
    }

    private static void putText(Map<String, Object> out, String key, String value) {
        if (value == null) {
            return;
        }
        String trimmed = value.trim();
        if (!trimmed.isEmpty()) {
            out.put(key, trimmed);
        }
    }
}
