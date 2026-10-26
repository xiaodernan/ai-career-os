package com.careeros.contract;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * A {@code @Transactional} annotation is a promise that Spring's proxy will open a transaction --
 * and a call an object makes on itself never reaches that proxy. So a writer reached only through
 * {@code this.write(...)} from a method that carries no transaction of its own files its rows one
 * commit at a time, and a refusal halfway through leaves the earlier rows behind.
 * {@code JobService.importJob -> persistImport} shipped in exactly that shape (#268): a paste the
 * database refused still added a company and a job to the catalog. {@link
 * com.careeros.job.service.JobImportAtomicityIT} is the behaviour witness for the one site that is
 * now fixed, by running the writes inside a {@code TransactionTemplate}.
 *
 * <p>This gate is the census of the rest. In every service-layer class, a same-file call into a
 * method that writes two or more rows must be armed -- either the caller carries
 * {@code @Transactional}, or the call sits inside a transaction-template lambda. The un-armed sites
 * are named below with the number of rows at stake, and the list is compared in both directions: a
 * new site reddens the build, and a site fixed but left listed reddens it too. Clearing an entry
 * takes the behaviour witness first, not the deletion.
 *
 * <p>"Rows" counts write statements one call can execute in sequence. A write inside a branch that
 * {@code return}s is left out, because that branch exits and never shares a path with the rows after
 * it -- an upsert that saves once per branch files one row, not two -- while a loop or a lambda
 * body keeps its writes, since a lambda's {@code return} hands a value back rather than leaving.
 */
class SelfInvokedTransactionContractTest {

    private static final Path MAIN = Path.of("src", "main", "java");

    /** A 4-space indented method declaration: a modifier, then the name, then the parameter list. */
    private static final Pattern DECL =
            Pattern.compile("^\\s{4}(public|protected|private)[^=;{]*?\\b([A-Za-z_]\\w*)\\s*\\(");
    private static final Pattern WRITE = Pattern.compile(
            "([A-Za-z_]\\w*)\\.\\s*(save|saveAll|saveAndFlush|delete|deleteAll|deleteById)\\s*\\(");
    /** A branch that hands a value back leaves the path the statements after it would take. */
    private static final Pattern RETURN_IN = Pattern.compile("\\breturn\\b");
    /** `delete` is not only a repository verb. */
    private static final Set<String> NOT_A_REPOSITORY = Set.of("sb", "builder", "buffer", "string");
    private static final Set<String> NOT_A_METHOD = Set.of(
            "class", "interface", "enum", "record", "if", "for", "while", "switch", "return", "new");

    /**
     * One entry per self-invocation that still commits its rows one transaction at a time: the
     * class, the entering method, the writer it calls on itself, and how many rows are at stake.
     */
    private static final List<String> NOT_YET_ATOMIC = List.of(
            "ConversationService.java#chat() -> persistTurn() 3 rows",
            "FileIngestService.java#persistRowsOnly() -> persistRows() 3 rows",
            "FileIngestService.java#uploadAndIngest() -> persistRows() 3 rows",
            "InterviewService.java#finalize() -> persistFinalization() 2 rows",
            "ResumeService.java#parse() -> persistParse() 7 rows",
            "ResumeService.java#upload() -> persistUpload() 4 rows");

    @Test
    @DisplayName("the census of un-armed writers is exactly the list, in both directions")
    void unarmedSitesAreExactlyTheListedOnes() throws IOException {
        assertThat(Files.isDirectory(MAIN))
                .as(MAIN + " is not under the run directory " + Path.of("").toAbsolutePath())
                .isTrue();
        List<String> found = new ArrayList<>();
        try (Stream<Path> files = Files.walk(MAIN)) {
            for (Path path : files.filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> List.of(p.toString().split("[/\\\\]")).contains("service"))
                    .toList()) {
                found.addAll(sites(blanke(Files.readString(path)), path.getFileName().toString())
                        .stream().map(Site::label).toList());
            }
        }
        // An absence claim needs a population: an empty walk would agree with an empty list.
        assertThat(found)
                .as("the walk reached no multi-write self-invocation, so it read no source")
                .isNotEmpty();
        assertThat(found.stream().sorted().toList()).isEqualTo(NOT_YET_ATOMIC);
    }

    @Test
    @DisplayName("the row counts come from the same bodies the charge reads")
    void writeCountsAreReadFromTheBodiesThemselves() throws IOException {
        Map<String, String> jobs = bodiesOf("job", "service", "JobService.java");
        // persistImport files the company and the JD itself and reaches the job row only through
        // a private helper: a count that stopped at the body would read two and charge the site
        // for the wrong reason.
        assertThat(jobs).containsKeys("persistImport", "buildJob");
        assertThat(writesOf("buildJob", jobs)).isEqualTo(1);
        assertThat(writesOf("persistImport", jobs)).isEqualTo(3);

        // The two shapes the count has to tell apart, read off shipped code rather than a plant:
        // upsertSkill saves once per branch and files one row, persistTurn files three in sequence.
        assertThat(writesOf("upsertSkill", bodiesOf("resume", "service", "ResumeService.java")))
                .isEqualTo(1);
        assertThat(writesOf("persistTurn", bodiesOf("conversation", "service", "ConversationService.java")))
                .isEqualTo(3);
    }

    /** The method bodies of one main-source file, comments and literals already blanked. */
    private static Map<String, String> bodiesOf(String... segments) throws IOException {
        return bodies(blanke(Files.readString(
                MAIN.resolve("com").resolve("careeros").resolve(String.join("/", segments)))));
    }

    @Test
    @DisplayName("the parser charges an unarmed site and clears the ways of arming it")
    void theParserGradesItsOwnVerdicts() {
        String offender = planted("@Transactional", "persist(p)", "");
        assertThat(sites(blanke(offender), "PlantedService.java"))
                .extracting(Site::label)
                .containsExactly("PlantedService.java#run() -> persist() 2 rows");

        // Armed by the caller's own transaction.
        assertThat(sites(blanke(plantedWithArmedCaller()), "PlantedService.java")).isEmpty();

        // Armed by a transaction template around the call -- the shape JobService.importJob chose,
        // because the analyst's answer must be waited for outside any transaction.
        assertThat(sites(blanke(planted("", "tx.execute(s -> persist(p))", "")), "PlantedService.java"))
                .isEmpty();

        // `this.persist(p)` is the same call written a second way, and the census owes it a verdict.
        assertThat(sites(blanke(planted("@Transactional", "this.persist(p)", "")), "PlantedService.java"))
                .extracting(Site::label)
                .containsExactly("PlantedService.java#run() -> persist() 2 rows");

        // One row is one statement: the database commits it atomically whatever the proxy does.
        assertThat(sites(blanke(planted("", "persist(p)", "remove")), "PlantedService.java")).isEmpty();

        // Two saves that never share a path: the first branch hands the row back and exits, so the
        // method files one row however the proxy is armed. This is upsertSkill's real shape.
        assertThat(sites(blanke(exclusiveBranch()), "PlantedService.java")).isEmpty();

        // A lambda's `return` hands a value to its caller, not out of the method: the row it filed
        // is still on the path of everything after, so this writer is charged with both of them.
        assertThat(sites(blanke(lambdaReturned()), "PlantedService.java"))
                .extracting(Site::label)
                .containsExactly("PlantedService.java#run() -> persist() 2 rows");

        // A writer named only in prose is not a call into it.
        assertThat(sites(blanke(planted("", "\"persist(\" + p.name()", "")), "PlantedService.java"))
                .isEmpty();
    }

    /** The shape the census charges: an un-armed caller, a writer of two rows. */
    private static String planted(String persistAnnotation, String call, String trim) {
        return "public class PlantedService {\n"
                + "    public Row run(Planner p) {\n"
                + "        return " + call + ";\n"
                + "    }\n"
                + "\n"
                + "    " + persistAnnotation + "\n"
                + "    public Row persist(Planner p) {\n"
                + "        accounts.save(p.one());\n"
                + (trim.isEmpty() ? "        accounts.save(p.two());\n" : "")
                + "        return p.row();\n"
                + "    }\n"
                + "}\n";
    }

    private static String plantedWithArmedCaller() {
        return "public class PlantedService {\n"
                + "    @Transactional\n"
                + "    public Row run(Planner p) {\n"
                + "        return persist(p);\n"
                + "    }\n"
                + "\n"
                + "    public Row persist(Planner p) {\n"
                + "        accounts.save(p.one());\n"
                + "        accounts.save(p.two());\n"
                + "        return p.row();\n"
                + "    }\n"
                + "}\n";
    }

    /** The upsert shape: one write per branch, and the branch that fires hands its row back and leaves. */
    private static String exclusiveBranch() {
        return "public class PlantedService {\n"
                + "    public Row run(Planner p) {\n"
                + "        return persist(p);\n"
                + "    }\n"
                + "\n"
                + "    public Row persist(Planner p) {\n"
                + "        if (p.known()) {\n"
                + "            return accounts.save(p.touch());\n"
                + "        }\n"
                + "        return accounts.save(p.fresh());\n"
                + "    }\n"
                + "}\n";
    }

    /** One write inside a mapping lambda that returns it, one after the stream: both on one path. */
    private static String lambdaReturned() {
        return "public class PlantedService {\n"
                + "    public Row run(Planner p) {\n"
                + "        return persist(p);\n"
                + "    }\n"
                + "\n"
                + "    public Row persist(Planner p) {\n"
                + "        Row first = p.candidates().stream().map(c -> {\n"
                + "            return accounts.save(c);\n"
                + "        }).findFirst().orElse(null);\n"
                + "        return audit.save(first);\n"
                + "    }\n"
                + "}\n";
    }

    record Site(String label) {
    }

    /** Offences in one class: same-file calls into writers that no transaction covers. */
    private static List<Site> sites(String source, String fileName) {
        Map<String, String> bodies = bodies(source);
        Map<String, Boolean> transactional = transactions(source);
        List<Site> out = new ArrayList<>();
        for (Map.Entry<String, String> caller : bodies.entrySet()) {
            boolean armed = Boolean.TRUE.equals(transactional.get(caller.getKey()))
                    || caller.getValue().contains("tx.execute(");
            if (armed) {
                continue;
            }
            for (String writer : bodies.keySet()) {
                if (writer.equals(caller.getKey())) {
                    continue;
                }
                int writes = writesOf(writer, bodies);
                if (writes >= 2 && calls(caller.getValue(), writer)) {
                    out.add(new Site(fileName + "#" + caller.getKey() + "() -> " + writer + "() "
                            + writes + " rows"));
                }
            }
        }
        return out;
    }

    /** True when the body really invokes `name(`, spelled with or without `this.`. */
    private static boolean calls(String body, String name) {
        return body.matches("(?s).*(?:[^\\w.]|this\\.)" + Pattern.quote(name) + "\\s*\\(.*");
    }

    private static int writesOf(String method, Map<String, String> bodies) {
        Set<String> seen = new LinkedHashSet<>();
        collect(method, bodies, seen, 0);
        return seen.size();
    }

    /** Writes in the body itself, plus the writes of the same-file helpers it calls. */
    private static void collect(String method, Map<String, String> bodies, Set<String> seen, int depth) {
        String body = bodies.getOrDefault(method, "");
        for (String hit : writeStatements(body)) {
            seen.add(method + "@" + hit);
        }
        if (depth >= 1) {
            return;
        }
        for (String helper : bodies.keySet()) {
            if (!helper.equals(method) && calls(body, helper)) {
                collect(helper, bodies, seen, depth + 1);
            }
        }
    }

    /**
     * Each write statement that can share an execution path with another one, keyed by where it
     * sits: two saves to one repository are two rows, so a key of `repo.save` alone would read one.
     * A write whose innermost block returns is left out -- that branch exits, so its row is never
     * on the path of the rows after it -- while a loop or lambda body keeps its writes, since every
     * turn adds another row to the same transaction.
     */
    private static List<String> writeStatements(String body) {
        Shape shape = blocks(body);
        List<String> out = new ArrayList<>();
        Matcher m = WRITE.matcher(body);
        while (m.find()) {
            if (NOT_A_REPOSITORY.contains(m.group(1))) {
                continue;
            }
            int block = m.start() < shape.at().length ? shape.at()[m.start()] : -1;
            if (block > 0 && shape.exit()[block]) {
                continue;
            }
            out.add(m.start() + ":" + m.group(1) + "." + m.group(2));
        }
        return out;
    }

    /** Per character the innermost block holding it, and per block whether its text returns. */
    private record Shape(int[] at, boolean[] exit) {
    }

    private static Shape blocks(String body) {
        int[] at = new int[body.length()];
        List<int[]> span = new ArrayList<>();
        List<Boolean> arrow = new ArrayList<>();
        List<Integer> stack = new ArrayList<>();
        for (int i = 0; i < body.length(); i += 1) {
            char ch = body.charAt(i);
            if (ch == '{') {
                stack.add(span.size());
                span.add(new int[] { i, body.length() - 1 });
                // `x -> { ... return ...; }` hands a value back to the caller of the lambda, not out
                // of the method: its write is still on the path of the statements that follow.
                arrow.add(priorIsLambdaArrow(body, i));
            } else if (ch == '}' && !stack.isEmpty()) {
                span.get(stack.remove(stack.size() - 1))[1] = i;
            }
            at[i] = stack.isEmpty() ? -1 : stack.get(stack.size() - 1);
        }
        boolean[] exit = new boolean[span.size()];
        for (int b = 0; b < span.size(); b += 1) {
            exit[b] = !arrow.get(b)
                    && RETURN_IN.matcher(body.substring(span.get(b)[0] + 1, span.get(b)[1])).find();
        }
        return new Shape(at, exit);
    }

    /** True when the `{` at `at` opens a lambda body rather than an if, loop or switch block. */
    private static boolean priorIsLambdaArrow(String body, int at) {
        int i = at - 1;
        while (i >= 0 && Character.isWhitespace(body.charAt(i))) {
            i -= 1;
        }
        return i >= 1 && body.charAt(i) == '>' && body.charAt(i - 1) == '-';
    }

    /** name -> body, for every 4-space indented method. Overloads share one entry, unioned. */
    private static Map<String, String> bodies(String source) {
        Map<String, String> out = new LinkedHashMap<>();
        String[] lines = source.split("\r?\n", -1);
        for (int i = 0; i < lines.length; i += 1) {
            Matcher m = DECL.matcher(lines[i]);
            if (!m.find() || NOT_A_METHOD.contains(m.group(2))) {
                continue;
            }
            String name = m.group(2);
            int depth = 0;
            boolean opened = false;
            for (int j = i; j < lines.length; j += 1) {
                String line = lines[j];
                if (!opened && line.contains(";")) {
                    break;  // an interface or abstract declaration has no body here
                }
                for (char ch : line.toCharArray()) {
                    if (ch == '{') {
                        depth += 1;
                        opened = true;
                    } else if (ch == '}') {
                        depth -= 1;
                    }
                }
                if (opened && depth == 0) {
                    String body = String.join("\n", Arrays.copyOfRange(lines, i, j + 1));
                    out.merge(name, body, (a, b) -> a + "\n" + b);
                    break;
                }
            }
        }
        return out;
    }

    /** Whether each declaration carries a @Transactional that is more than a read-only marker. */
    private static Map<String, Boolean> transactions(String source) {
        Map<String, Boolean> out = new LinkedHashMap<>();
        String[] lines = source.split("\r?\n", -1);
        for (int i = 0; i < lines.length; i += 1) {
            Matcher m = DECL.matcher(lines[i]);
            if (!m.find()) {
                continue;
            }
            boolean annotated = false;
            for (int j = i - 1; j >= 0; j -= 1) {
                String prior = lines[j].trim();
                if (prior.isEmpty() || prior.startsWith("*") || prior.startsWith("//")
                        || prior.startsWith("/*") || prior.startsWith("@")) {
                    if (prior.startsWith("@") && prior.contains("Transactional")
                            && !prior.contains("readOnly = true")) {
                        annotated = true;
                    }
                    continue;
                }
                break;
            }
            out.putIfAbsent(m.group(2), annotated);
        }
        return out;
    }

    /**
     * Comments, string literals and char literals replaced by spaces of the same length, so the
     * line numbers a body is read at do not move and nothing a comment merely names can be
     * mistaken for code.
     */
    private static String blanke(String source) {
        char[] c = source.toCharArray();
        int i = 0;
        while (i < c.length) {
            char ch = c[i];
            if (ch == '/' && i + 1 < c.length && c[i + 1] == '/') {
                while (i < c.length && c[i] != '\n') {
                    c[i++] = ' ';
                }
            } else if (ch == '/' && i + 1 < c.length && c[i + 1] == '*') {
                while (i < c.length && !(c[i] == '*' && i + 1 < c.length && c[i + 1] == '/')) {
                    if (c[i] != '\n') {
                        c[i] = ' ';
                    }
                    i += 1;
                }
                if (i < c.length) {
                    c[i] = ' ';
                    c[i + 1] = ' ';
                    i += 2;
                }
            } else if (ch == '"' || ch == '\'') {
                char quote = ch;
                c[i++] = ' ';
                while (i < c.length && c[i] != quote) {
                    if (c[i] == '\\') {
                        c[i++] = ' ';
                    }
                    if (i < c.length && c[i] != '\n') {
                        c[i] = ' ';
                    }
                    i += 1;
                }
                if (i < c.length) {
                    c[i] = ' ';
                }
            } else {
                i += 1;
            }
        }
        return new String(c);
    }
}
