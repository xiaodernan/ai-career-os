package com.careeros.job.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.job.dto.SavedSearchDtos.SavedSearchItem;
import com.careeros.job.dto.SavedSearchDtos.SavedSearchRequest;
import com.careeros.job.service.SavedSearchService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * Saved searches over HTTP (roadmap 19.1). A saved search is the board's own
 * filters kept under a name; every route is scoped to the caller, so one user's
 * saved questions are never another's to read or delete.
 */
@RestController
@RequestMapping("/api/v1/saved-searches")
public class SavedSearchController {

    private final SavedSearchService savedSearches;

    public SavedSearchController(SavedSearchService savedSearches) {
        this.savedSearches = savedSearches;
    }

    @GetMapping
    public List<SavedSearchItem> list(@CurrentUser AuthUser user) {
        return savedSearches.list(user.id());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public SavedSearchItem create(@CurrentUser AuthUser user,
                                  @RequestBody @Valid SavedSearchRequest request) {
        return savedSearches.create(user.id(), request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@CurrentUser AuthUser user, @PathVariable UUID id) {
        savedSearches.delete(user.id(), id);
    }
}
