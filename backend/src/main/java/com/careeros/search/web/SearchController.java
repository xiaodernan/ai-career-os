package com.careeros.search.web;

import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUser;
import com.careeros.search.dto.SearchDtos.SearchResponse;
import com.careeros.search.service.SearchService;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/search")
public class SearchController {

    private final SearchService search;

    public SearchController(SearchService search) {
        this.search = search;
    }

    @GetMapping
    public SearchResponse search(@CurrentUser AuthUser user, @RequestParam String q) {
        if (q == null || q.isBlank()) {
            return new SearchResponse("", java.util.List.of(), java.util.List.of(), java.util.List.of(),
                    java.util.List.of(), java.util.List.of(), java.util.List.of());
        }
        return search.search(user.id(), q);
    }
}
