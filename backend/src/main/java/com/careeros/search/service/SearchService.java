package com.careeros.search.service;

import com.careeros.search.dto.SearchDtos.SearchResponse;
import com.careeros.search.repository.SearchRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** GET /api/v1/search — one read-only pass across all typed groups, capped per group. */
@Service
public class SearchService {

    private static final int GROUP_CAP = 5;

    private final SearchRepository search;
    private final QueryEmbeddingService embeddingService;

    public SearchService(SearchRepository search, QueryEmbeddingService embeddingService) {
        this.search = search;
        this.embeddingService = embeddingService;
    }

    @Transactional(readOnly = true)
    public SearchResponse search(UUID userId, String q) {
        String term = q.trim();
        List<Double> embedding = embeddingService.embed(term, userId);
        return new SearchResponse(
                term,
                search.jobs(userId, term, GROUP_CAP, embedding),
                search.companies(term, GROUP_CAP),
                search.resumes(userId, term, GROUP_CAP),
                search.notes(userId, term, GROUP_CAP),
                search.conversations(userId, term, GROUP_CAP),
                search.applications(userId, term, GROUP_CAP));
    }
}
