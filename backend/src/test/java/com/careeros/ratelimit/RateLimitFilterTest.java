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
        // The 10.2 bridge: the aggregate report and the granular engines that will join
        // under the same prefix are all engine calls, not reads.
        assertThat(RateLimitFilter.ruleFor("/api/v1/growth-report")).isEqualTo("ai");
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
    void theAddressMoveIsMeteredAsMailNotAsAi() {
        // Every call mails a confirmation and a warning, so the route is a relay, not a model
        // call. It is its own bucket because the AI ceiling (30/min) would let one account
        // write sixty letters a minute to an address it names.
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/email-change")).isEqualTo("mail");
        assertThat(RateLimitFilter.ruleFor("/api/v1/users/me/email-change")).isEqualTo("mail");
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/email-change/")).isEqualTo("mail");
        assertThat(RateLimitFilter.ruleFor("/api/v1/users/me/email-change/")).isEqualTo("mail");
    }

    @Test
    void theOtherAccountRoutesAreNotMailedEveryCall() {
        // The bucket exists for letters, not for the account surface: a route that is not wired
        // to the mail port stays a cheap write.
        assertThat(RateLimitFilter.ruleFor("/api/v1/me")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/password")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/users/me")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/email-change-notes")).isNull();
    }

    @Test
    void onlyTheRoutesThatJudgeACodeAreMeteredAsMfa() {
        // Guessing six digits is the attack; the meter is the account's. The status read and the
        // seed minting are outside on purpose: a settings screen polls one and may re-ask the
        // other, and neither answers a verdict on a code. The reprint and the disable judge one
        // too, so they share the bucket -- a stolen session cannot grind against a lost phone
        // through the newer doors either.
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/activate")).isEqualTo("mfa");
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/activate/")).isEqualTo("mfa");
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/recovery-codes")).isEqualTo("mfa");
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/recovery-codes/")).isEqualTo("mfa");
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/disable")).isEqualTo("mfa");
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/disable/")).isEqualTo("mfa");
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/enroll")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/me/mfa/activate/notes")).isNull();
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
    void theThreeIngestAndImportRoutesAlsoSpendMoney() {
        // Each of these reaches the ai-service and pays for it: /jobs/import runs the JD
        // analyst, the two upload routes embed every chunk of the document. They are not
        // reads, and leaving them out of the list means a scripted client can call them
        // without limit — which is exactly what this filter exists to prevent.
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs/import")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/knowledge/documents")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/resumes/upload")).isEqualTo("ai");
    }

    @Test
    void storingTextWithoutEmbeddingItStaysUnthrottled() {
        // Saving a note or creating a job row from pasted fields calls no model; classifying
        // these as AI cost would throttle ordinary data entry.
        assertThat(RateLimitFilter.ruleFor("/api/v1/knowledge/notes")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/resumes")).isNull();
        assertThat(RateLimitFilter.ruleFor("/api/v1/knowledge/sources")).isNull();
    }

    @Test
    void trailingSlashIsToleratedOnAiSubPaths() {
        assertThat(RateLimitFilter.ruleFor("/api/v1/resumes/abc/parse/")).isEqualTo("ai");
        assertThat(RateLimitFilter.ruleFor("/api/v1/jobs/xyz/match/")).isEqualTo("ai");
    }
}
