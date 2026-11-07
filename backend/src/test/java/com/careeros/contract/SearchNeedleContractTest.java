package com.careeros.contract;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * What a reader types into a search box is data, and there are exactly two ways this codebase asks
 * SQL whether a column contains it: a {@code LIKE} pattern whose wildcards were neutralised by
 * {@link com.careeros.common.LikePattern}, or a JPQL {@code LOCATE} that has no pattern language to
 * misunderstand the value with.
 *
 * <p>A third spelling arrived anyway (58.1). {@code CompanyRepository} asked Spring Data for a derived
 * {@code findByNameContainingIgnoreCase...}, and the derived keyword wraps the argument in {@code %…%}
 * itself, with nothing between the reader's characters and the wildcard: {@code ?q=%} answered the
 * whole catalog, {@code ?q=a_b} matched a company named "axb", and a real "Acme_Data" could not be
 * found by typing its own name. The board's own comment about the fix says the defect was not the
 * search but the <em>spelling</em> -- which is why this gate reads the source rather than the result:
 * the query is legal SQL, it returns 200, and every row-based assertion on it looks like a search that
 * works. Only the shape of the binding distinguishes a search from a pattern.
 *
 * <p>The rules are global on purpose (no file may derive a containment query, no wildcard may be
 * hand-wrapped), and the roster of needle owners is pinned beside them so a list that picks up a
 * {@code q=} has to be named here before it can ship -- where "named" means the other three tests then
 * grade it. 70.1 is the fifth owner: the pipeline board's word arrives on the same route that already
 * carried {@code status} and {@code jobId}, so all three are one query rather than eight. 70.3 is the
 * sixth, and the one that answers a bare array: {@code GET /contacts} has no total beside its rows to
 * hint that a filter was dropped, so a wrong needle here is invisible in the envelope and visible only
 * in the people the registry stopped showing. 70.4 is the seventh: the rehearsals list, whose two
 * derived reads differed only by whether a card id had been set, so a word would have arrived as the
 * fourth permutation of a pair rather than as a query of its own. It is also the list whose columns a
 * reader leaves empty by construction -- a rehearsal started from a job has no company recorded -- so
 * the {@code COALESCE} here is a correctness requirement rather than tidiness.
 */
class SearchNeedleContractTest {

    private static final Path MAIN = Path.of("src", "main", "java");

    /** Every shipped needle, by path from the source root. The census is of the whole population. */
    private static final Set<String> NEEDLE_OWNERS = Set.of(
            "com/careeros/job/repository/JobSearchRepository.java",
            "com/careeros/job/repository/CompanyRepository.java",
            "com/careeros/search/repository/SearchRepository.java",
            "com/careeros/inbound/repository/InboundMailRepository.java",
            "com/careeros/application/repository/ApplicationRepository.java",
            "com/careeros/network/repository/ContactRepository.java",
            "com/careeros/interview/repository/InterviewSessionRepository.java");

    /** {@code setParameter("companyLike", ...)} -- the site where a reader's value becomes a pattern. */
    private static final Pattern LIKE_BINDING =
            Pattern.compile("setParameter\\(\"(\\w*Like)\",\\s*([^)]*)\\)");

    /** A derived {@code ...Containing...} query method declaration, in a repository interface. */
    private static final Pattern DERIVED_CONTAINMENT = Pattern.compile(
            "(?m)^\\s+[\\w<>?, .]+\\s+\\w*(Containing|Contains|Matches|Regex)\\w*\\s*\\(");

    /** The signature of the defect: a {@code %} the code puts in front of the value by hand. */
    private static final Pattern HAND_WRAPPED_WILDCARD = Pattern.compile("\"%\"\\s*\\+");

    /** The one file allowed to write wildcards, named so the roster can be read without it. */
    private static final String ESCAPING_HELPER = "com/careeros/common/LikePattern.java";

    private List<Path> sources() {
        try (Stream<Path> walk = Files.walk(MAIN)) {
            List<Path> out = new ArrayList<>();
            walk.filter(p -> p.toString().endsWith(".java")).forEach(out::add);
            return out;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private String read(Path path) {
        try {
            return Files.readString(path);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private String from(Path path) {
        return MAIN.relativize(path).toString().replace('\\', '/');
    }

    /**
     * A file that consults one of the two neutralised spellings. The helper that owns the escaping
     * rule is skipped by name rather than by shape: its javadoc quotes {@code ILIKE} to explain what
     * it protects against, and a list that documents a needle it no longer binds is exactly what the
     * next two tests would want to ask.
     */
    private Set<String> needleOwners() {
        Set<String> found = new TreeSet<>();
        for (Path path : sources()) {
            String rel = from(path);
            if (rel.equals(ESCAPING_HELPER)) {
                continue;
            }
            String text = read(path);
            if (text.contains("ILIKE ") || text.contains("LOCATE(:") || text.contains("LikePattern.contains")) {
                found.add(rel);
            }
        }
        return found;
    }

    @Test
    @DisplayName("the lists that read a reader's words are a named population, not an accident")
    void theNeedleRosterIsCensused() {
        assertThat(needleOwners()).containsExactlyInAnyOrderElementsOf(NEEDLE_OWNERS);
        // The rule has to live somewhere, and the roster deliberately does not name it: an owner that
        // composes its own wildcards would pass the tests above and reopen this one.
        assertThat(read(MAIN.resolve(ESCAPING_HELPER))).contains("return \"%\" + escaped + \"%\";");
    }

    @Test
    @DisplayName("a value bound as a LIKE pattern comes from the one place that neutralises wildcards")
    void everyLikeBindingIsEscapedAtTheSite() {
        for (Path path : sources()) {
            Matcher call = LIKE_BINDING.matcher(read(path));
            while (call.find()) {
                assertThat(call.group(2).trim())
                        .as("%s binds %s from somewhere other than LikePattern -- the escaping rule "
                                        + "lives in the helper, so a hand-built pattern at the call site "
                                        + "re-opens the defect this gate was written for",
                                from(path), call.group(1))
                        .startsWith("LikePattern.contains(");
            }
        }
    }

    @Test
    @DisplayName("no repository derives a containment query from a method name")
    void aDerivedKeywordIsNotAPatternLanguage() {
        List<String> derived = new ArrayList<>();
        for (Path path : sources()) {
            if (!path.getFileName().toString().endsWith("Repository.java")) {
                continue;
            }
            Matcher declaration = DERIVED_CONTAINMENT.matcher(read(path));
            while (declaration.find()) {
                derived.add(from(path) + " -> " + declaration.group().trim());
            }
        }
        assertThat(derived).as(
                "a derived ...Containing.../...Matches... method wraps the caller's value in wildcards "
                        + "itself, so the reader's characters arrive at SQL as a pattern; the two "
                        + "spellings that answer the same question safely are LikePattern plus "
                        + "ESCAPE '!' and a JPQL LOCATE")
                .isEmpty();
    }

    @Test
    @DisplayName("the wildcards are written in exactly one file")
    void thePatternIsComposedWhereTheEscapingRuleLives() {
        List<String> handWrapped = new ArrayList<>();
        for (Path path : sources()) {
            String rel = from(path);
            if (rel.equals("com/careeros/common/LikePattern.java")) {
                continue;
            }
            if (HAND_WRAPPED_WILDCARD.matcher(read(path)).find()) {
                handWrapped.add(rel);
            }
        }
        assertThat(handWrapped).as(
                "a percent literal concatenated in front of a value is a wildcard the reader did not "
                        + "type; LikePattern.contains is the only place allowed to add it, because it "
                        + "is also the only place that neutralises the ones already in the value")
                .isEmpty();
    }

    @Test
    @DisplayName("the company board's needle is the LOCATE spelling, ordered by the column its pages partition")
    void theCompaniesBranchKeepsTheSpellingThatReplacedTheDefect() {
        String repo = read(MAIN.resolve("com/careeros/job/repository/CompanyRepository.java"));
        assertThat(repo).contains("LOCATE(:needle, LOWER(c.name)) > 0")
                .contains("ORDER BY c.name ASC")
                // The name survives in this file's prose, which explains what the query replaced; a
                // declaration of it is the defect, so that is the shape refused here.
                .doesNotContain("Page<Company> findByNameContaining");
    }

    @Test
    @DisplayName("the registry's needle reads the five columns a profile may leave blank")
    void theContactsBranchReadsEveryColumnTheDialogWrites() {
        String repo = read(MAIN.resolve("com/careeros/network/repository/ContactRepository.java"));
        assertThat(repo).contains("LOCATE(:needle, LOWER(c.name)) > 0")
                // `name` is the one column the schema refuses to leave empty. The other five are the
                // dialog's optionals, and a person with no company recorded is still a person -- an
                // unguarded `LOWER(c.role)` on a null column is not a miss, it is a NULL, and NULL is
                // never greater than zero, so the search would silently skip every thin profile.
                .contains("LOWER(COALESCE(c.role, ''))", "LOWER(COALESCE(c.company, ''))",
                        "LOWER(COALESCE(c.relation, ''))", "LOWER(COALESCE(c.email, ''))",
                        "LOWER(COALESCE(c.notes, ''))")
                // Blank is the whole registry, not a search for the empty string.
                .contains(":needle = ''")
                .doesNotContain("Containing");
    }

    @Test
    @DisplayName("the rehearsals list keeps both of its scopes inside one query")
    void theRehearsalsBranchKeepsTheTwoScopesInOneQuery() {
        String repo = read(MAIN.resolve("com/careeros/interview/repository/InterviewSessionRepository.java"));
        assertThat(repo)
                // A rehearsal started from a job records no company, and one started free-form
                // records no position: those two columns are empty by construction, so an
                // unguarded LOWER() on them would drop the row from the answer rather than miss
                // the word in it.
                .contains("LOCATE(:needle, LOWER(COALESCE(s.companyName, ''))) > 0")
                .contains("LOCATE(:needle, LOWER(COALESCE(s.positionTitle, ''))) > 0")
                .contains("LOCATE(:needle, LOWER(s.mode)) > 0")
                .contains(":needle = ''")
                // The card id is a second scope on top of the user, never a replacement for it,
                // and never a reason to grow a second query for the same board.
                .contains(":applicationId IS NULL OR s.applicationId = :applicationId")
                .contains("ORDER BY s.startedAt DESC, s.id ASC")
                .doesNotContain("Containing")
                .doesNotContain("findByUserIdOrderByStartedAtDescIdAsc")
                .doesNotContain("findByUserIdAndApplicationIdOrderByStartedAtDescIdAsc");
    }
}
