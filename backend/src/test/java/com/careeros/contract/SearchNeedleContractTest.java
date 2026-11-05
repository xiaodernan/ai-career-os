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
 * carried {@code status} and {@code jobId}, so all three are one query rather than eight.
 */
class SearchNeedleContractTest {

    private static final Path MAIN = Path.of("src", "main", "java");

    /** Every shipped needle, by path from the source root. The census is of the whole population. */
    private static final Set<String> NEEDLE_OWNERS = Set.of(
            "com/careeros/job/repository/JobSearchRepository.java",
            "com/careeros/job/repository/CompanyRepository.java",
            "com/careeros/search/repository/SearchRepository.java",
            "com/careeros/inbound/repository/InboundMailRepository.java",
            "com/careeros/application/repository/ApplicationRepository.java");

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
}
