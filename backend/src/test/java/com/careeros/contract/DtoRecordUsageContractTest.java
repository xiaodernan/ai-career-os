package com.careeros.contract;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * A DTO record is a claim that something on the wire has this shape.
 *
 * <p>Nothing in Java fails when that claim stops being true: an unreferenced record compiles, passes
 * every test, and reads like a contract the next person has to keep in step with an endpoint that
 * never answers with it. #154 found two -- {@code JobDtos.TailorResponse} (the tailor route returns
 * ai-service's own map, and the frontend interface of that name is a different table entirely) and
 * {@code InterviewDtos.TurnPayload} (the relay builds {@code TurnItem}s) -- and both had been kept
 * alive only by their own plausibility.
 *
 * <p>The population is the shipped {@code *Dtos.java} files; a use is the name appearing in any other
 * main source or in a test. This gate's own package is excluded from that search, because a table that
 * names an exception would otherwise create the usage it is trying to deny.
 */
class DtoRecordUsageContractTest {

    private static final Path MAIN = Path.of("src", "main", "java");
    private static final Path TEST = Path.of("src", "test", "java");

    /** Records declared and answered with nothing, each with the reason it is allowed to stay. */
    private static final Map<String, String> DECLARED_UNANSWERED = Map.of();

    private static final Pattern RECORD = Pattern.compile("\\brecord\\s+(\\w+)\\s*[<(]");

    @Test
    void everyDtoRecordIsAnsweredSomewhere() {
        Map<String, String> declarations = declaredRecords();
        Set<String> unused = new TreeSet<>(declarations.keySet());
        unused.removeAll(usedNames(declarations));
        unused.removeAll(declaredExceptions());

        assertThat(unused).as("DTO records nothing constructs or returns — delete them or write down "
                + "why they stay: " + unused).isEmpty();
    }

    /**
     * Positive control, and the reason this test builds its own little world to read: with every real
     * record used, the assertion above is satisfied by an empty set, which a reader that found no
     * declarations at all would also satisfy.
     */
    @Test
    void theReaderNamesARecordNobodyUses() {
        Map<String, String> sources = Map.of(
                "com/x/OneDtos.java", "public record UsedHere(String a) {}\n"
                        + "public record Orphaned(String b) {}\n",
                "com/x/Two.java", "class Two { UsedHere x; }");
        Map<String, String> declarations = new LinkedHashMap<>();
        sources.forEach((file, body) -> RECORD.matcher(body).results()
                .forEach(m -> declarations.put(m.group(1), file)));
        assertThat(declarations.keySet()).containsExactlyInAnyOrder("UsedHere", "Orphaned");

        Set<String> unused = new TreeSet<>(declarations.keySet());
        unused.removeAll(usedIn(sources, declarations));
        assertThat(unused).containsExactly("Orphaned");
    }

    /** The scan is over real files, and the count is a floor rather than a restatement of one name. */
    @Test
    void thePopulationIsTheOneThisGateClaims() {
        Map<String, String> declarations = declaredRecords();
        assertThat(declarations).as("no *Dtos.java record was read").hasSizeGreaterThanOrEqualTo(70);
        assertThat(declarations.keySet()).contains("TailorRequest", "MatchSummary", "TurnItem");
        assertThat(usedNames(declarations)).as("the usage scan found no record in use at all")
                .contains("MatchSummary", "TurnItem");
    }

    /**
     * Exceptions are keyed by the thing they excuse -- the record's name -- and are only honoured
     * while that record is still declared, so an exemption cannot outlive the thing it was written
     * for. The reason string is what a reader sees, and it has to be a reason.
     */
    private static Set<String> declaredExceptions() {
        Map<String, String> declarations = declaredRecords();
        DECLARED_UNANSWERED.forEach((name, why) -> {
            assertThat(declarations).as("an exemption names %s, which is no longer declared", name)
                    .containsKey(name);
            assertThat(why.trim()).as("%s is exempted with no reason", name).isNotEmpty();
        });
        return DECLARED_UNANSWERED.keySet();
    }

    /** Every {@code record X(} declared in a shipped DTO file, as name -> file. */
    private static Map<String, String> declaredRecords() {
        Map<String, String> found = new LinkedHashMap<>();
        dtoFiles().forEach((file, body) -> RECORD.matcher(body)
                .results().forEach(m -> found.put(m.group(1), file)));
        return found;
    }

    private static Set<String> usedNames(Map<String, String> declarations) {
        return usedIn(allSources(), declarations);
    }

    /** Names that appear somewhere other than the line that declares them. */
    private static Set<String> usedIn(Map<String, String> sources, Map<String, String> declarations) {
        Set<String> used = new TreeSet<>();
        sources.forEach((file, body) -> {
            List<String> lines = body.lines().toList();
            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i);
                for (String name : declarations.keySet()) {
                    if (!line.contains(name)) {
                        continue;
                    }
                    boolean declaration = line.matches(".*\\brecord\\s+" + name + "\\s*[<(].*");
                    boolean inItsOwnFile = declarations.get(name).equals(file);
                    if (!declaration || !inItsOwnFile) {
                        used.add(name);
                    }
                }
            }
        });
        return used;
    }

    private static Map<String, String> allSources() {
        Map<String, String> sources = new LinkedHashMap<>(dtoFiles());
        try (Stream<Path> walk = Stream.concat(Files.walk(MAIN), Files.walk(TEST))) {
            walk.filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> !p.startsWith(TEST.resolve("com").resolve("careeros").resolve("contract")))
                    .filter(p -> !p.toString().endsWith("Dtos.java"))
                    .forEach(p -> sources.put(relative(p), read(p)));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return sources;
    }

    private static Map<String, String> dtoFiles() {
        Map<String, String> files = new LinkedHashMap<>();
        try (Stream<Path> walk = Files.walk(MAIN)) {
            walk.filter(p -> p.toString().endsWith("Dtos.java")).forEach(p -> files.put(relative(p), read(p)));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        assertThat(files).as("no *Dtos.java under " + MAIN).isNotEmpty();
        return files;
    }

    private static String relative(Path p) {
        return p.toString().replace('\\', '/');
    }

    private static String read(Path p) {
        try {
            return Files.readString(p);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
