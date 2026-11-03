package com.careeros.inbound.repository;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.Query;

/**
 * The one thing a mocked service test cannot see: the query a page actually runs (49.3).
 *
 * <p>The page's search is a single JPQL string, so the service test can only say that the
 * words travel to the repository. This test reads the string itself and asks whether every
 * field a reader might remember is searched -- the envelope's four, and the letter's own
 * body -- and whether the two filters are still beside it rather than quietly dropped when
 * the search grew.
 */
class InboundMailRepositoryQueryTest {

    @Test
    void thePageQueryReadsTheWholeLetterAndKeepsBothFilters() throws NoSuchMethodException {
        Query query = InboundMailRepository.class
                .getMethod("findPage", UUID.class, String.class, String.class, boolean.class,
                        Pageable.class)
                .getAnnotation(Query.class);

        assertThat(query).as("findPage is an annotated query, not a derived one").isNotNull();
        String jpql = query.value().toLowerCase(Locale.ROOT);
        assertThat(jpql)
                .as("the search reads every field a reader might remember")
                .contains("m.subject", "m.fromaddress", "m.company", "m.role", "m.bodytext")
                .contains(":intent", ":unread");
    }

    @Test
    void theChipCountsReadTheSameFieldsAsThePage() throws NoSuchMethodException {
        // The chip and the page it opens must answer one question. The two queries keep the
        // five-field predicate side by side rather than sharing a string, so this test says
        // out loud that the copy is deliberate and that a field added to one is added here.
        Query query = InboundMailRepository.class
                .getMethod("countByIntent", UUID.class, String.class)
                .getAnnotation(Query.class);

        assertThat(query).as("countByIntent is an annotated query").isNotNull();
        assertThat(query.value().toLowerCase(Locale.ROOT))
                .as("the counts narrow under the same words as the page")
                .contains("m.subject", "m.fromaddress", "m.company", "m.role", "m.bodytext")
                .contains("group by m.intent");
    }
}
