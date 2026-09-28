package com.careeros.search.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Component;

/**
 * Shared query embedding service with caching. Used by both JobService and SearchService
 * so the same cached vectors serve both the jobs board and the global search.
 */
@Component
public class QueryEmbeddingService {

    private final AiServiceClient ai;

    /** Caches query → embedding vectors. Key is the raw query text. Entries expire after
     * 12 hours (provider changes are rare and require restart anyway), and the cache is
     * capped at 10k entries to bound memory. Empty/failed results are not cached so
     * transient failures are retried. */
    private final Cache<String, List<Double>> embeddingCache = Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(12, TimeUnit.HOURS)
            .build();

    public QueryEmbeddingService(AiServiceClient ai) {
        this.ai = ai;
    }

    /**
     * Returns the embedding vector for the given query, or null if the query is blank,
     * the provider is unavailable, or the response is empty. Results are cached by query
     * text (12h TTL, 10k max) so repeated searches don't re-embed. Empty/failed results
     * are not cached so transient failures are retried.
     */
    public List<Double> embed(String q, UUID userId) {
        if (q == null || q.isBlank()) {
            return null;
        }
        List<Double> cached = embeddingCache.getIfPresent(q);
        if (cached != null) {
            return cached;
        }
        try {
            Map<String, Object> embedded = ai.embedQuery(q, userId);
            List<Object> values = Json.arr(embedded.get("embedding"));
            List<Double> vector = new ArrayList<>(values.size());
            for (Object value : values) {
                if (!(value instanceof Number number)) {
                    return null;
                }
                vector.add(number.doubleValue());
            }
            if (!vector.isEmpty()) {
                embeddingCache.put(q, vector);
            }
            return vector.isEmpty() ? null : vector;
        } catch (ApiException e) {
            return null;
        }
    }

    /** Clears the embedding cache. Public for test access. */
    public void clearCache() {
        embeddingCache.invalidateAll();
    }
}