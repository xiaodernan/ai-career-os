package com.careeros.ratelimit;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

/**
 * Path classification for the rate limiter. Pure and offline — the point is that
 * "which paths cost money" is a decision worth pinning in a test, because getting it
 * wrong is invisible: the endpoints simply go unthrottled.
 */
class RateLimitFilterTest {

    @Test
    void authPathsUseTheAuthBucket() {
        assertThat(RateLimitFilter.ruleFor("/api/v1/auth/login")).isEqualTo("auth");
        assertThat(RateLimitFilter.ruleFor("/api/v1/auth/register")).isEqualTo("auth");
        assertThat(RateLimitFilter.ruleFor("/api/v1/auth/refresh")).isEqualTo("auth");
    }

    @Test
    void streamingAiUsesTheAiBucket() {
        assertThat(RateLimitFilter.ruleFor("/api/v1/ai/stream/abc")).isEqualTo("ai");
    }

    @Test
    void blockingAiEndpointsAreLimitedToo() {
        // The agent turn is the single most expensive call in the product and lives
        // under /copilot, not /ai — limiting only /ai left it wide open.
        assertThat(RateLimitFilter.ruleFor("/api/v1/copilot/chat")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/interview/sessions")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/interview/sessions/xyz/answer")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/jds")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/jds/suggestions")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/knowledge/text")).isEqualTo("ai");
    }

    @Test
    void aiSubPathsOfCheapResourcesAreLimited() {
        String job = "/api/v1/jobs/6b0178a0-d352-09c3-ea65-8f107bd28d01";
        assertThat(RateLimitFilter.ruleFor(job + "/match")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor(job + "/tailor")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor(job + "/cover-letter")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/resumes/abc/parse")).isEqualTo("ai");
    }

    @Test
    void cheapReadsAreNotLimited() {
        // Browsing must not be throttled, or the product becomes unusable.
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs/saved")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/resumes")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/applications")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/reports/dashboard")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/search")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/health")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/companies/abc")).isNull();
    }

    @Test
    void aJobIdThatMerelyContainsAnAiWordIsNotLimited() {
        // Guard against a sloppy prefix match: only the trailing segment counts.
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs/match")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs/matching-engine")).isNull();
    }

    @Test
    void trailingSlashIsToleratedOnAiSubPaths() {
        assertThat(RateLimitFilter.ruleFor("/api/v1/resumes/abc/parse/")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs/xyz/match/")).isEqualTo("ai");
    }
}
