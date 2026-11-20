package com.careeros.algorithm;

import java.util.Locale;

/**
 * Deterministic compatibility score between a reader's skills and a job's demands
 * (Epic 186) — the zero-cost ranking signal for jobs that have no match row yet.
 *
 * <p>The engine's authoritative ranking is the computed match (JobMatch.overall);
 * this class exists for the rows that come BEFORE that: the dashboard's recommended
 * list, where jobs the reader never scored would otherwise order arbitrarily. The
 * score is deliberately simple — overlap over normalized skill tokens with a
 * containment credit so "spring boot" meets "spring" — and it never claims to be
 * the match: the dashboard renders it only as an order, never as a percentage.
 *
 * <p>Tokenization is lowercase-and-split on non-letter runs (ASCII and CJK both
 * survive: a posting demanding "Kafka" and a resume claiming "Kafka 集群经验" still
 * meet on the token), because skills arrive comma-separated, slash-separated and as
 * free text in the same tables.
 */
public final class Recommendation {

  private Recommendation() {}

  /** Compatibility in [0,1]: skill overlap (with containment credit) x experience ratio. */
  public static double score(String candidateSkills, String jobSkills, int candidateYears, int requiredYears) {
    java.util.Set<String> have = tokens(candidateSkills);
    java.util.Set<String> want = tokens(jobSkills);
    if (want.isEmpty()) {
      return have.isEmpty() ? 0.0 : 0.5; // nothing demanded: no signal either way
    }
    if (have.isEmpty()) {
      return 0.0;
    }
    int matched = 0;
    for (String wantToken : want) {
      if (have.contains(wantToken)) {
        matched++;
        continue;
      }
      // Containment credit, one direction per demand token so it is not double-counted.
      for (String haveToken : have) {
        if (haveToken.contains(wantToken) || wantToken.contains(haveToken)) {
          matched++;
          break;
        }
      }
    }
    double overlap = (double) matched / want.size();
    double experience = requiredYears > 0 && candidateYears > 0
        ? Math.min(1.0, (double) candidateYears / requiredYears)
        : 1.0;
    return Math.min(1.0, overlap * experience);
  }

  /** Lowercased letter-tokens; punctuation splits, digits ride along (go, react18). */
  static java.util.Set<String> tokens(String raw) {
    java.util.Set<String> out = new java.util.HashSet<>();
    if (raw == null) {
      return out;
    }
    for (String token : raw.toLowerCase(Locale.ROOT).split("[^\\p{L}\\p{Nd}#+.]+")) {
      String clean = token.strip();
      if (!clean.isEmpty() && clean.length() >= 2) {
        out.add(clean);
      }
    }
    return out;
  }
}
