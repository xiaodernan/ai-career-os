package com.careeros.algorithm;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

/**
 * The two deterministic rankers the abandoned package left behind, now actually used:
 * {@link Recommendation} orders the dashboard's unscored jobs, {@link TopK} keeps the
 * strongest of them. The cases pin what the dashboard relies on — containment credit,
 * CJK tokens surviving, the empty-input contracts — because a ranker that misreads
 * its input silently reorders the reader's first screen.
 */
class AlgorithmTest {

    @Test
    void containmentCreditMeetsSpringInsideSpringBoot() {
        double score = Recommendation.score("Spring Boot, PostgreSQL, Redis",
                "Java, Spring, PostgreSQL", 5, 5);
        // spring is met by containment ("spring boot" contains it) and postgresql exactly;
        // java is a genuine miss. 2 of 3 demands met -- the ratio is the honest answer.
        assertThat(score).isCloseTo(2.0 / 3.0, within(1e-9));
    }

    @Test
    void fullContainmentAcrossEveryDemandScoresOne() {
        double score = Recommendation.score("Spring Boot 3, PostgreSQL, Redis",
                "Spring, PostgreSQL", 4, 4);
        assertThat(score).isEqualTo(1.0);
    }

    @Test
    void cjkTokensSurviveTokenization() {
        double score = Recommendation.score("Kafka 集群经验", "Kafka", 3, 3);
        assertThat(score).isEqualTo(1.0);
    }

    @Test
    void anEmptyDemandAnswersHalf_notAFalseZero() {
        // A job with no stated skills is not "0% compatible" — it is unscored, and the
        // dashboard renders the order only; 0.5 keeps such rows mid-deck, not at the bottom.
        assertThat(Recommendation.score("Java", "", 1, 0)).isEqualTo(0.5);
        assertThat(Recommendation.score("", "Java", 1, 0)).isZero();
    }

    @Test
    void experienceRatioFoldsIntoTheScore() {
        double full = Recommendation.score("Java, Kafka", "Java, Kafka", 5, 5);
        double short_ = Recommendation.score("Java, Kafka", "Java, Kafka", 2, 4);
        assertThat(full).isEqualTo(1.0);
        assertThat(short_).isEqualTo(0.5);
    }

    @Test
    void topKKeepsTheStrongestAndTheirOrder() {
        String[] jobs = {"weak", "strongest", "middle", "none"};
        int[] kept = TopK.select(jobs, 2, job ->
                switch (job) {
                    case "strongest" -> 1.0;
                    case "middle" -> 0.5;
                    case "weak" -> 0.25;
                    default -> 0.0;
                });
        assertThat(kept).containsExactly(1, 2);
    }
}
