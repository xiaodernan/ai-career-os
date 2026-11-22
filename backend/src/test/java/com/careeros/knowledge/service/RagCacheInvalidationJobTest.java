package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Epic 417, consumer half: a reader that turns a stream entry back into a bump.
 *
 * <p>The producer writes one field and this handler reads one field, and the two are separate
 * processes that may not even be the same version of the code. Everything pinned here is that
 * seam: the wire name, the field name, and what an entry that fails to name an owner does --
 * which is the case a rolling deploy produces and no test of {@link RagCacheInvalidator} can
 * reach, because that class only ever writes a well-formed payload.
 *
 * <p>The bump itself is mocked. Its behaviour -- the ai-service that refuses, the counter that
 * records the outcome -- belongs to {@link RagCacheInvalidatorTest}; repeating it here would
 * pin the same rule twice and grade nothing about this seam.
 */
class RagCacheInvalidationJobTest {

    private static final UUID USER = UUID.fromString("00000000-0000-0000-0000-0000000000bb");

    private final RagCacheInvalidator invalidator = mock(RagCacheInvalidator.class);
    private final RagCacheInvalidationJob job = new RagCacheInvalidationJob(invalidator);

    @Test
    void theKindIsTheNameTheProducerEnqueuesUnder() {
        // A rename here is a silent no-handler dead-letter: the worker finds nothing for the
        // wire name and every entry goes to the dead stream, so the name is pinned as a string.
        assertThat(job.kind()).isEqualTo("rag.cache.invalidate");
        assertThat(RagCacheInvalidationJob.KIND).isEqualTo(job.kind());
    }

    @Test
    void theFieldIsTheOneTheProducerWrites() {
        assertThat(RagCacheInvalidationJob.USER_FIELD).isEqualTo("userId");
    }

    @Test
    void anEntryNamingAnOwnerBumpsThatOwnerAndNothingElse() {
        job.handle(Map.of(RagCacheInvalidationJob.USER_FIELD, USER.toString()));

        verify(invalidator).bump(USER);
    }

    @Test
    void anEntryThatNamesNoReadableUserIsAcknowledgedInsteadOfRetried() {
        List<Map<String, String>> unusable = List.of(
                Map.of(),
                Map.of(RagCacheInvalidationJob.USER_FIELD, ""),
                Map.of(RagCacheInvalidationJob.USER_FIELD, "00000000-0000-0000-0000"),
                Map.of("user", USER.toString()));

        for (Map<String, String> payload : unusable) {
            // Throwing would be the honest-looking wrong answer: the entry stays pending, a
            // sibling runs the same garbage, and five deliveries later it is dead-lettered --
            // a retry ladder climbing a flight of stairs that cannot be climbed.
            assertThatCode(() -> job.handle(payload)).as("payload %s", payload).doesNotThrowAnyException();
        }

        verify(invalidator, never()).bump(any());
    }
}
