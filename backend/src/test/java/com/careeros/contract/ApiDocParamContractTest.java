package com.careeros.contract;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.annotation.JsonAlias;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Method;
import java.lang.reflect.Parameter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.springframework.core.annotation.AnnotatedElementUtils;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * docs/API.md is the contract a hand-written client, a script or an agent reads before it
 * calls the platform. Spring binds a query parameter by name and ignores any name it does not
 * recognise — so a parameter the doc spells wrong is not an error, it is a filter that quietly
 * stops filtering: {@code GET /jobs?remoteType=remote} answers 200 with the whole board.
 *
 * The names the endpoint really binds come from the compiled controllers, not from a copy kept
 * next to this test, so the two sides can only agree by one of them actually changing.
 */
class ApiDocParamContractTest {

    private static final Path MAIN = Path.of("src", "main", "java");
    private static final Path DOC = Path.of("..", "docs", "API.md");
    private static final String API_PREFIX = "/api/v1";

    /** Rows that must keep spelling their parameters out, so the gate cannot be dodged by deleting the list. */
    private static final List<String> MUST_DOCUMENT = List.of("/jobs", "/applications", "/companies",
            "/activity/runs", "/search", "/memories", "/knowledge/sources");

    @Test
    void everyParameterTheDocAdvertisesIsOneTheEndpointBinds() {
        Map<String, Set<String>> bound = boundParams();
        documentedRows().forEach((path, documented) -> {
            Set<String> real = bound.get(path);
            assertThat(real).as("GET %s is documented with parameters but no controller binds it", path)
                    .isNotNull();
            Set<String> phantom = new TreeSet<>(documented);
            phantom.removeAll(real);
            assertThat(phantom).as("GET %s documents parameters Spring silently drops", path).isEmpty();
        });
    }

    @Test
    void aRowThatNamesOneParameterNamesAllOfThem() {
        Map<String, Set<String>> bound = boundParams();
        documentedRows().forEach((path, documented) -> {
            Set<String> real = bound.get(path);
            assertThat(real).as("GET %s resolves to a real endpoint", path).isNotNull();
            Set<String> forgotten = new TreeSet<>(real);
            forgotten.removeAll(documented);
            assertThat(forgotten).as("GET %s binds parameters the doc never mentions", path).isEmpty();
        });
    }

    /**
     * A row that quotes a snake_case name without offering it is explaining where a value comes
     * from, and the name has to be one the platform actually puts on a wire.
     *
     * Before this rule, every quoted name in a GET row was read as a filter claim, so the digest
     * row's honest sentence -- that an impossible {@code applied_at} arrives through the caller's
     * own import -- was reported as advertising a parameter no endpoint binds. The way that
     * pressure gets resolved is the sentence disappearing from the doc, which is what happened.
     * Declining to grade it as a parameter is not a licence to say anything: an invented key is a
     * field an integrator will look for in the answer and never find.
     *
     * <p>The mail-settings row quotes a second vocabulary: {@code MAIL_LINK_INVALID} is an error
     * code, not a field, and it is read on the wire as {@code error.code}. Those names are graded
     * against {@link com.careeros.common.ApiErrorCode} instead -- a typo in a code the doc
     * promises is exactly as invisible to a client as a field that never arrives.
     */
    @Test
    void everyProseNameAGetRowQuotesIsAKeyTheBackendWrites() {
        Set<String> keys = backendWireKeys();
        Set<String> codes = errorCodes();
        List<String> invented = new ArrayList<>();
        documentedProse().forEach((path, names) -> names.stream()
                .filter(name -> !keys.contains(name) && !codes.contains(name))
                .forEach(name -> invented.add(path + " quotes `" + name
                        + "`, which no backend source writes and no ApiErrorCode declares")));
        assertThat(invented).as("a GET row names a snake_case field the platform does not use")
                .isEmpty();
    }

    /** The names {@code error.code} answers with, read off the enum rather than copied. */
    private static Set<String> errorCodes() {
        Set<String> names = new TreeSet<>();
        for (com.careeros.common.ApiErrorCode code : com.careeros.common.ApiErrorCode.values()) {
            names.add(code.name());
        }
        return names;
    }

    @Test
    void theRowsThatCarryTheContractStayWritten() {
        Map<String, Set<String>> documented = documentedRows();
        MUST_DOCUMENT.forEach(row -> assertThat(documented)
                .as("GET %s has to keep listing its parameters — an empty row is not a checked row", row)
                .containsKey(row));
    }

    /**
     * Positive control: both scanners read real bodies. An unparsed doc or a controller list that
     * failed to load would leave every assertion above vacuously green.
     */
    @Test
    void bothSidesOfTheComparisonAreActuallyRead() throws IOException {
        Map<String, Set<String>> bound = boundParams();
        assertThat(bound).hasSizeGreaterThan(20);
        // `q` arrives by parameter name, which only Spring's -parameters compile retains; an
        // unprefixed `arg0` here would mean the reflection is reading a build the doc cannot match.
        assertThat(bound.get("/jobs")).contains("q", "minSalary", "remote");
        assertThat(documentedRows().get("/jobs")).contains("minSalary");
        // the classifier reads a filter named in prose ("optional `kinds` filter") as the claim it
        // is, or the new prose branch would be quietly swallowing every parameter row in the table
        assertThat(documentedRows().get("/memories")).contains("kinds");
        assertThat(documentedProse()).as("no GET row quotes a name outside a filter clause -- "
                + "the prose branch would be grading an empty population").isNotEmpty();
        assertThat(backendWireKeys()).as("the literal walk over src/main/java found no wire key")
                .contains("applied_at");
        assertThat(errorCodes()).as("the error-code vocabulary the prose rule consults was read")
                .contains("MAIL_LINK_INVALID", "LOGIN_SESSION_NOT_FOUND");
        assertThat(exampleQueries()).hasSizeGreaterThanOrEqualTo(2);
        assertThat(Files.readString(DOC)).contains("## 2. Public API");
    }

    /**
     * A table row is read by a human who then types the URL; the worked examples are the ones that
     * get pasted straight into a shell, so a wrong name there is a command that runs and lies.
     */
    @Test
    void theWorkedExamplesOnlyAskForParametersThatBind() {
        Map<String, Set<String>> bound = boundParams();
        List<String> ignored = new ArrayList<>();
        exampleQueries().forEach(call -> {
            Set<String> real = bound.get(documentedForm(call.getKey()));
            assertThat(real).as("the examples call GET %s, which no controller maps", call.getKey())
                    .isNotNull();
            if (!real.contains(call.getValue())) {
                ignored.add(call.getKey() + "?" + call.getValue());
            }
        });
        assertThat(ignored).as("an example asks for a parameter Spring ignores").isEmpty();
    }

    /** Every (path, parameter name) pair the curl examples actually put on the wire. */
    private static List<Map.Entry<String, String>> exampleQueries() {
        List<Map.Entry<String, String>> pairs = new ArrayList<>();
        Matcher url = Pattern.compile("\\$B(/[^?\"' ]+)\\?([^\"' ]+)").matcher(String.join("\n", lines()));
        while (url.find()) {
            for (String assignment : url.group(2).split("&")) {
                String name = assignment.split("=")[0];
                if (name.matches("[A-Za-z][A-Za-z0-9_]*")) {
                    pairs.add(Map.entry(url.group(1), name));
                }
            }
        }
        return pairs;
    }

    /** A controller method's HTTP verb, its doc-shaped path, and what it binds from the request. */
    private record Route(String verb, String path, Set<String> queryNames, Class<?> bodyType,
                         Class<?> returnType) {
    }

    private static List<Route> routes() {
        List<Route> out = new ArrayList<>();
        for (String className : controllerClasses()) {
            Class<?> controller;
            try {
                controller = Class.forName(className, false, ApiDocParamContractTest.class.getClassLoader());
            } catch (ClassNotFoundException e) {
                throw new IllegalStateException("walked a source file that is not on the test classpath: "
                        + className, e);
            }
            RequestMapping root = AnnotatedElementUtils.findMergedAnnotation(controller, RequestMapping.class);
            String basePath = root == null ? "" : firstOf(root.path(), root.value());
            for (Method method : controller.getDeclaredMethods()) {
                String verb = verbOf(method);
                RequestMapping route = AnnotatedElementUtils.findMergedAnnotation(method, RequestMapping.class);
                String path = basePath + (route == null ? "" : firstOf(route.path(), route.value()));
                if (verb.isEmpty() || !path.startsWith(API_PREFIX)) {
                    continue;
                }
                Set<String> names = new LinkedHashSet<>();
                Class<?> bodyType = null;
                for (Parameter p : method.getParameters()) {
                    RequestParam param = AnnotatedElementUtils.findMergedAnnotation(p, RequestParam.class);
                    if (param != null) {
                        names.add(first(param.name(), param.value(), p.getName()));
                    }
                    if (AnnotatedElementUtils.hasAnnotation(p,
                            org.springframework.web.bind.annotation.RequestBody.class)) {
                        bodyType = p.getType();
                    }
                }
                out.add(new Route(verb, documentedForm(path.replaceFirst("^" + API_PREFIX, "")),
                        names, bodyType, method.getReturnType()));
            }
        }
        return out;
    }

    /**
     * Jackson drops a body property the target record has no component for — no error, no
     * warning, just a request that proceeds as if the caller had not sent it. So a field the doc
     * names for a POST/PATCH/PUT body has to be a field the record actually binds, and a row that
     * names any of them names all of them unless it says {@code ...}.
     */
    @Test
    void everyBodyFieldTheDocNamesIsOneTheRecordBinds() {
        Map<String, BodySpec> bound = boundBodies();
        List<String> phantoms = new ArrayList<>();
        documentedBodies().forEach((key, row) -> {
            BodySpec real = bound.get(key);
            assertThat(real).as("%s is documented with a body but no controller binds one", key)
                    .isNotNull();
            if (real.freeForm()) {
                return; // a Map body has no field set to be wrong about
            }
            Set<String> phantom = new TreeSet<>(row.names());
            phantom.removeAll(real.accepted());
            if (!phantom.isEmpty()) {
                phantoms.add(key + " names " + phantom);
            }
        });
        assertThat(phantoms).as("documented body fields Jackson silently drops").isEmpty();
    }

    /**
     * The rows that were wrong when this gate was written have to keep naming fields, so the gate
     * cannot be passed by collapsing them to {@code {...}}.
     */
    @Test
    void theBodyRowsThatCarryTheContractStayWritten() {
        Map<String, BodyRow> rows = documentedBodies();
        for (String key : List.of("PATCH /applications/{}", "PUT /applications/{}/reorder",
                "PATCH /me", "POST /auth/password/reset", "POST /copilot/chat",
                "POST /interview/sessions")) {
            assertThat(rows).as("%s has to keep listing its body fields", key).containsKey(key);
        }
    }

    /**
     * Compared against the components, not the accepted spellings: {@code @JsonAlias} adds
     * snake_case ways to say the same field, and the doc's job is to name each field once.
     */
    @Test
    void aBodyRowThatNamesFieldsNamesAllOfThem() {
        Map<String, BodySpec> bound = boundBodies();
        List<String> omissions = new ArrayList<>();
        documentedBodies().forEach((key, row) -> {
            BodySpec real = bound.get(key);
            assertThat(real).as("%s resolves to a real endpoint", key).isNotNull();
            if (real.freeForm() || row.openEnded()) {
                return;
            }
            Set<String> forgotten = new TreeSet<>(real.components());
            forgotten.removeAll(row.names());
            if (!forgotten.isEmpty()) {
                omissions.add(key + " also binds " + forgotten);
            }
        });
        assertThat(omissions).as("body fields an endpoint binds but the caller is never told about")
                .isEmpty();
    }

    /** The walk sees request records at all, and reads their aliases as well as their names. */
    @Test
    void theBodySideOfTheWalkIsActuallyRead() {
        Map<String, BodySpec> bound = boundBodies();
        assertThat(bound).hasSizeGreaterThan(10);
        BodySpec match = bound.get("POST /jobs/{}/match");
        assertThat(match.components()).contains("resumeVersionId").doesNotContain("resume_version_id");
        // the alias is an accepted spelling, not a second field the doc has to list
        assertThat(match.accepted()).contains("resumeVersionId", "resume_version_id");
        assertThat(bound.get("PATCH /interview/sessions/{}").freeForm()).isTrue();
        assertThat(documentedBodies()).containsKey("POST /interview/sessions");
    }

    /** GET paths (without the /api/v1 prefix, one segment folded to {}) to the names they bind. */
    private static Map<String, Set<String>> boundParams() {
        Map<String, Set<String>> out = new HashMap<>();
        for (Route r : routes()) {
            if ("GET".equals(r.verb())) {
                out.putIfAbsent(r.path(), r.queryNames());
            }
        }
        return out;
    }

    /**
     * "POST /jobs/{}/match" to what its request record accepts. {@code freeForm} marks the bodies
     * declared as a Map — those take any key, so the phantom rule has nothing to say about them.
     */
    private static Map<String, BodySpec> boundBodies() {
        Map<String, BodySpec> out = new HashMap<>();
        for (Route r : routes()) {
            if (r.bodyType() == null) {
                continue;
            }
            java.lang.reflect.RecordComponent[] components = r.bodyType().getRecordComponents();
            if (components == null) {
                out.putIfAbsent(r.verb() + " " + r.path(), new BodySpec(Set.of(), Set.of(), true));
                continue;
            }
            Set<String> names = new LinkedHashSet<>();
            Set<String> accepted = new LinkedHashSet<>();
            for (java.lang.reflect.RecordComponent c : components) {
                names.add(c.getName());
                accepted.add(c.getName());
                accepted.addAll(aliasesOf(c));
            }
            out.putIfAbsent(r.verb() + " " + r.path(), new BodySpec(names, accepted, false));
        }
        return out;
    }

    /**
     * A record component carries an annotation like {@code @JsonAlias} onto its field and its
     * accessor, and {@link java.lang.reflect.RecordComponent} is not itself an annotated element,
     * so the aliases are read from whichever of the two the compiler put them on.
     */
    private static List<String> aliasesOf(java.lang.reflect.RecordComponent component) {
        JsonAlias alias = AnnotatedElementUtils.findMergedAnnotation(component.getAccessor(), JsonAlias.class);
        if (alias == null) {
            try {
                alias = AnnotatedElementUtils.findMergedAnnotation(component.getAccessor()
                        .getDeclaringClass().getDeclaredField(component.getName()), JsonAlias.class);
            } catch (NoSuchFieldException e) {
                return List.of();
            }
        }
        return alias == null ? List.of() : Arrays.asList(alias.value());
    }

    /** What one endpoint's body binds: its fields, plus every spelling Jackson accepts for them. */
    private record BodySpec(Set<String> components, Set<String> accepted, boolean freeForm) {
    }

    /** The doc folds a UUID or a task id to one shape; so must the resolved route. */
    private static String documentedForm(String path) {
        return path.replaceAll("\\{[^}]*}", "{}");
    }

    private static String verbOf(Method method) {
        if (AnnotatedElementUtils.hasAnnotation(method, GetMapping.class)) {
            return "GET";
        }
        if (AnnotatedElementUtils.hasAnnotation(method, PostMapping.class)) {
            return "POST";
        }
        if (AnnotatedElementUtils.hasAnnotation(method, PutMapping.class)) {
            return "PUT";
        }
        if (AnnotatedElementUtils.hasAnnotation(method, PatchMapping.class)) {
            return "PATCH";
        }
        if (AnnotatedElementUtils.hasAnnotation(method, DeleteMapping.class)) {
            return "DELETE";
        }
        RequestMapping raw = AnnotatedElementUtils.findMergedAnnotation(method, RequestMapping.class);
        if (raw != null && raw.method().length == 1) {
            return raw.method()[0].name();
        }
        return "";
    }

    private static List<String> controllerClasses() {
        if (!Files.isDirectory(MAIN)) {
            throw new IllegalStateException("expected the module directory as the working directory, found "
                    + Path.of("").toAbsolutePath());
        }
        try (Stream<Path> files = Files.walk(MAIN)) {
            List<String> sources = files.filter(p -> p.getFileName().toString().endsWith("Controller.java"))
                    .map(p -> MAIN.relativize(p).toString().replace('\\', '/'))
                    .map(p -> p.substring(0, p.length() - ".java".length()))
                    .toList();
            assertThat(sources).isNotEmpty();
            return sources.stream().map(s -> s.replace('/', '.')).toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** A documented body row: the field names it spells out, and whether it admits more with "...". */
    private record BodyRow(Set<String> names, boolean openEnded) {
    }

    private static final List<String> BODY_VERBS = List.of("POST", "PATCH", "PUT");

    /** "POST /jobs" to the first brace group of its request sentence — never the answer. */
    private static Map<String, BodyRow> documentedBodies() {
        Map<String, BodyRow> rows = new TreeMap<>();
        boolean inPublicApi = false;
        for (String line : lines()) {
            if (line.startsWith("## ")) {
                inPublicApi = line.startsWith("## 2. Public API");
                continue;
            }
            if (!inPublicApi || !line.startsWith("|")) {
                continue;
            }
            String[] cells = line.replace("\\|", "¦").split("\\|");
            if (cells.length < 4 || !BODY_VERBS.contains(cells[1].trim())) {
                continue;
            }
            String path = cells[2].trim().replace("`", "");
            String notes = String.join(" ", Arrays.copyOfRange(cells, 3, cells.length));
            // The request is what the row says before it answers: an arrow in most rows, and in
            // a body-less POST (the ingestion apply) the word "Answers". Reading past either read
            // that row's answer `{created, updated, closed, appliedAt}` as a body nothing binds.
            int stop = notes.length();
            int arrow = notes.indexOf('→');
            if (arrow >= 0) {
                stop = Math.min(stop, arrow);
            }
            int answers = notes.indexOf("Answers");
            if (answers >= 0) {
                stop = Math.min(stop, answers);
            }
            Matcher group = Pattern.compile("\\{([^{}]*)}").matcher(notes.substring(0, stop));
            if (!group.find()) {
                continue;
            }
            Set<String> names = new LinkedHashSet<>();
            boolean openEnded = false;
            for (String token : group.group(1).split(",")) {
                String candidate = token.trim().replace("?", "");
                if (candidate.equals("...")) {
                    openEnded = true;
                } else if (candidate.matches("[A-Za-z][A-Za-z0-9_]*")) {
                    // snake_case is how the aliases are spelled: filtering it out would hide a
                    // documented field no record accepts, which is the whole point of this rule
                    names.add(candidate);
                }
            }
            if (!names.isEmpty()) {
                rows.put(cells[1].trim() + " " + documentedForm(path), new BodyRow(names, openEnded));
            }
        }
        return rows;
    }

    /** Path in the doc (without the prefix) to the parameter names its Notes cell spells out. */
    private static Map<String, Set<String>> documentedRows() {
        Map<String, Set<String>> rows = new HashMap<>();
        getRows().forEach((path, row) -> {
            if (!row.parameters().isEmpty()) {
                rows.put(path, row.parameters());
            }
        });
        return rows;
    }

    /** Path in the doc to the snake_case names it quotes to describe a value, not to offer a filter. */
    private static Map<String, Set<String>> documentedProse() {
        Map<String, Set<String>> rows = new HashMap<>();
        getRows().forEach((path, row) -> {
            if (!row.prose().isEmpty()) {
                rows.put(path, row.prose());
            }
        });
        return rows;
    }

    /** A GET row's Notes cell, split by what each quoted name is claiming to be. */
    private record GetRow(Set<String> parameters, Set<String> prose) {
    }

    /** How this doc says "here is something the caller sends". */
    private static final Pattern PARAMETER_CLAUSE = Pattern.compile(
            "(?i)\\b(query|queries|parameters?|filters?|search|sort|optional|pagination|repeatable)\\b");

    private static Map<String, GetRow> getRows() {
        Map<String, GetRow> rows = new TreeMap<>();
        boolean inPublicApi = false;
        for (String line : lines()) {
            if (line.startsWith("## ")) {
                inPublicApi = line.startsWith("## 2. Public API");
                continue;
            }
            if (!inPublicApi || !line.startsWith("|")) {
                continue;
            }
            String[] cells = line.replace("\\|", "¦").split("\\|");
            if (cells.length < 4 || !"GET".equals(cells[1].trim())) {
                continue;
            }
            String path = cells[2].trim().replace("`", "");
            if (!path.startsWith("/")) {
                continue;
            }
            GetRow row = classify(String.join(" ", Arrays.copyOfRange(cells, 3, cells.length)));
            if (!row.parameters().isEmpty() || !row.prose().isEmpty()) {
                rows.put(documentedForm(path), row);
            }
        }
        assertThat(rows).as("no GET row in the public API table quotes a name at all").isNotEmpty();
        return rows;
    }

    /**
     * Reads either spelling, and only inside backticks: a backticked {@code a, b, c} list, a
     * {@code ?a=&b=} query string, or a name the sentence is describing.
     *
     * Two shapes still count as a filter claim, and they are the whole of what this scan used to
     * grade: anything spelled as an assignment (a caller pasting it into a URL is pasting that),
     * and every name that is not snake_case -- a bare {@code kinds} or {@code minSalary} in a GET
     * row has only ever been a parameter here. A snake_case name outside a clause that introduces
     * filters is the one case the old rule over-read, and it is graded by
     * {@link #everyProseNameAGetRowQuotesIsAKeyTheBackendWrites} instead of dropped.
     */
    private static GetRow classify(String notes) {
        Set<String> parameters = new LinkedHashSet<>();
        Set<String> prose = new LinkedHashSet<>();
        Matcher quoted = Pattern.compile("`([^`]*)`").matcher(notes);
        while (quoted.find()) {
            String chunk = quoted.group(1);
            boolean offered = chunk.contains("=")
                    || PARAMETER_CLAUSE.matcher(clause(notes, quoted.start())).find();
            for (String token : chunk.split("[,&]")) {
                String candidate = token.trim().replaceAll("^[?]", "").split("[=|\\s]")[0];
                if (candidate.matches("[A-Za-z][A-Za-z0-9_]*")) {
                    // underscores stay in the graded population either way: dropping them here is
                    // what once hid a documented filter no endpoint binds
                    (offered || !candidate.contains("_") ? parameters : prose).add(candidate);
                }
            }
        }
        return new GetRow(parameters, prose);
    }

    /** The sentence a quote sits in, which is what says whether the row offers the name or describes it. */
    private static String clause(String notes, int at) {
        int from = 0;
        for (int i = Math.min(at, notes.length()) - 1; i >= 0; i--) {
            if (isStop(notes.charAt(i))) {
                from = i + 1;
                break;
            }
        }
        int to = notes.length();
        for (int i = at; i < notes.length(); i++) {
            if (isStop(notes.charAt(i))) {
                to = i;
                break;
            }
        }
        return notes.substring(from, to);
    }

    private static boolean isStop(char c) {
        return c == '.' || c == ';' || c == '-' || c == '\u2014';
    }

    /**
     * The snake_case string literals the backend itself writes -- the names it actually puts on a
     * wire, whether into a bundle row, a bridge payload or a status map.
     */
    private static Set<String> backendWireKeys() {
        Set<String> keys = new TreeSet<>();
        Pattern literal = Pattern.compile("\"([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\"");
        try (Stream<Path> files = Files.walk(MAIN)) {
            for (Path source : files.filter(p -> p.getFileName().toString().endsWith(".java")).toList()) {
                Matcher m = literal.matcher(Files.readString(source));
                while (m.find()) {
                    keys.add(m.group(1));
                }
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        assertThat(keys).as("src/main/java writes no snake_case literal").isNotEmpty();
        return keys;
    }

    private static List<String> lines() {
        if (!Files.isReadable(DOC)) {
            throw new IllegalStateException("expected the repo docs next to the module, found "
                    + DOC.toAbsolutePath());
        }
        try {
            return Files.readAllLines(DOC);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String first(String... values) {
        for (String v : values) {
            if (v != null && !v.isEmpty()) {
                return v;
            }
        }
        return "";
    }

    /** A mapping annotation answers from either {@code path} or {@code value}, whichever it spells. */
    private static String firstOf(String[] primary, String[] fallback) {
        if (primary.length > 0 && !primary[0].isEmpty()) {
            return primary[0];
        }
        return fallback.length > 0 ? fallback[0] : "";
    }

    /* ------------------------------------------------------------------ documented answers */

    /**
     * What an endpoint answers with, as Jackson will serialize it.
     *
     * The third hand-typed copy of a shape: the record declares it, the browser reads it, and
     * docs/API.md is what a new integrator starts from. A key the row invents teaches a caller to
     * read `undefined`; a key it omits is a field no one learns to ask for.
     */
    private record AnswerSpec(Set<String> components, boolean freeForm) {
    }

    /** The keys a row names after its arrow, and whether "..." leaves the list open. */
    private record AnswerRow(Set<String> names, boolean openEnded) {
    }

    private static Map<String, AnswerSpec> boundAnswers() {
        Map<String, AnswerSpec> out = new TreeMap<>();
        for (Route route : routes()) {
            String key = route.verb() + " " + route.path();
            java.lang.reflect.RecordComponent[] fields = route.returnType().getRecordComponents();
            if (fields == null || com.careeros.common.PageDTO.class.isAssignableFrom(route.returnType())) {
                // a Map body is whatever ai-service answered with (its own gates read that), and a
                // paged row describes its item, not the envelope
                out.put(key, new AnswerSpec(Set.of(), true));
                continue;
            }
            Set<String> names = new LinkedHashSet<>();
            for (java.lang.reflect.RecordComponent field : fields) {
                names.add(field.getName());
            }
            out.put(key, new AnswerSpec(names, false));
        }
        return out;
    }

    /** "POST /copilot/chat" to the brace group that follows its arrow -- the answer, not the body. */
    private static Map<String, AnswerRow> documentedAnswers() {
        Map<String, AnswerRow> rows = new TreeMap<>();
        boolean inPublicApi = false;
        for (String line : lines()) {
            if (line.startsWith("## ")) {
                inPublicApi = line.startsWith("## 2. Public API");
                continue;
            }
            if (!inPublicApi || !line.startsWith("|")) {
                continue;
            }
            String[] cells = line.replace("\\|", "¦").split("\\|");
            if (cells.length < 4) {
                continue;
            }
            String verb = cells[1].trim();
            List<String> verbs = Arrays.stream(verb.split("/")).map(String::trim).toList();
            if (verbs.stream().noneMatch(BODY_VERBS::contains) && !verbs.contains("GET")) {
                continue;
            }
            String notes = String.join(" ", Arrays.copyOfRange(cells, 3, cells.length));
            int arrow = notes.indexOf('→');
            String afterArrow = arrow < 0 ? "" : notes.substring(arrow);
            Matcher group = Pattern.compile("\\{([^{}]*)}").matcher(afterArrow);
            if (!group.find()) {
                continue;
            }
            Set<String> names = new LinkedHashSet<>();
            boolean openEnded = false;
            for (String token : group.group(1).split(",")) {
                String candidate = token.trim().replace("?", "").replace("[]", "");
                if (candidate.equals("...")) {
                    openEnded = true;
                } else if (candidate.matches("[A-Za-z][A-Za-z0-9_]*")) {
                    // underscores stay legal names: the aliases this repo answers under are
                    // snake_case, and dropping them would hide exactly the drift worth finding
                    names.add(candidate);
                }
            }
            if (!names.isEmpty()) {
                rows.put(first(verbs.toArray(String[]::new)) + " "
                        + documentedForm(cells[2].trim().replace("`", "")), new AnswerRow(names, openEnded));
            }
        }
        return rows;
    }

    @Test
    void everyAnswerKeyTheDocNamesIsOneTheEndpointReturns() {
        Map<String, AnswerSpec> bound = boundAnswers();
        List<String> problems = new ArrayList<>();
        documentedAnswers().forEach((key, row) -> {
            AnswerSpec real = bound.get(key);
            assertThat(real).as("%s documents an answer but no controller serves it", key)
                    .isNotNull();
            if (real.freeForm()) {
                return;
            }
            Set<String> phantom = new TreeSet<>(row.names());
            phantom.removeAll(real.components());
            if (!phantom.isEmpty()) {
                problems.add(key + " is documented with " + phantom + ", which it never answers");
            }
        });
        assertThat(problems).isEmpty();
    }

    @Test
    void aRowThatNamesAnswerKeysNamesAllOfThem() {
        Map<String, AnswerSpec> bound = boundAnswers();
        List<String> problems = new ArrayList<>();
        documentedAnswers().forEach((key, row) -> {
            AnswerSpec real = bound.get(key);
            if (real == null || real.freeForm() || row.openEnded()) {
                return;
            }
            Set<String> forgotten = new TreeSet<>(real.components());
            forgotten.removeAll(row.names());
            if (!forgotten.isEmpty()) {
                problems.add(key + " answers " + forgotten + " that the row never names");
            }
        });
        assertThat(problems).isEmpty();
    }

    /** The one row that carries this half of the contract has to keep carrying it. */
    @Test
    void theAnswerRowsThatCarryTheContractStayWritten() {
        assertThat(documentedAnswers()).containsKey("POST /copilot/chat");
    }

    @Test
    void theAnswerSideOfTheWalkIsActuallyRead() {
        Map<String, AnswerSpec> bound = boundAnswers();
        assertThat(bound).hasSizeGreaterThan(20);
        AnswerSpec chat = bound.get("POST /copilot/chat");
        assertThat(chat.components()).contains("answer", "userMessageId", "assistantMessageId", "runId")
                .doesNotContain("task_id");
        assertThat(bound.get("GET /jobs").freeForm()).as("a paged row describes its item").isTrue();
        assertThat(documentedAnswers().get("POST /copilot/chat").names())
                .containsExactlyInAnyOrderElementsOf(chat.components());
    }

    /** Every path the public table names in backticks, folded the way the routes are. */
    private static Set<String> documentedPublicPaths() {
        Set<String> out = new TreeSet<>();
        boolean inPublicApi = false;
        for (String line : lines()) {
            if (line.startsWith("## ")) {
                inPublicApi = line.startsWith("## 2. Public API");
                continue;
            }
            if (!inPublicApi || !line.startsWith("|")) {
                continue;
            }
            Matcher path = Pattern.compile("`(/[A-Za-z0-9_/{}.-]*)`").matcher(line);
            while (path.find()) {
                out.add(documentedForm(path.group(1)));
            }
        }
        return out;
    }

    /**
     * A path the doc advertises and Spring does not serve is a 404 someone has to discover by
     * hand, so anything documented without a mapping behind it has to say why.
     */
    @Test
    void everyPublicPathTheDocNamesIsOneTheBackendServes() {
        Set<String> served = new TreeSet<>();
        for (Route route : routes()) {
            served.add(route.path());
        }
        Set<String> ghosts = new TreeSet<>(documentedPublicPaths());
        ghosts.removeAll(served);
        assertThat(ghosts).as("documented paths with no mapping behind them").isEqualTo(DOCUMENTED_BUT_NOT_SERVED);
        // measured floors: 58 distinct folded routes are served and the table names 50+ of them,
        // so neither side of the comparison can pass by having read nothing
        assertThat(served).hasSizeGreaterThanOrEqualTo(58);
        assertThat(documentedPublicPaths()).hasSizeGreaterThanOrEqualTo(50);
    }

    /**
     * The other direction: a route that exists and is not in the table is a feature nobody can
     * discover. Measured rather than assumed -- the set is the working list of undocumented
     * endpoints, and it has to shrink, never grow.
     */
    @Test
    void everyRouteTheBackendServesIsDocumented() {
        Set<String> documented = documentedPublicPaths();
        Set<String> undocumented = new TreeSet<>();
        for (Route route : routes()) {
            if (!documented.contains(route.path()) && !SERVED_BUT_NOT_DOCUMENTED.contains(route.path())) {
                undocumented.add(route.verb() + " " + route.path());
            }
        }
        assertThat(undocumented).isEqualTo(Set.of());
        // without the floor an empty route table would satisfy the rule the same way
        assertThat(routes()).as("the backend's own route table was read").hasSizeGreaterThanOrEqualTo(58);
    }

/** Paths that are documented in the Public API section but intentionally not served (exempt from "every documented path is served"). */
    private static final Set<String> DOCUMENTED_BUT_NOT_SERVED = Set.of();

    /** Paths that are served by the backend but intentionally not documented in the Public API section (exempt from "every served route is documented"). */
    private static final Set<String> SERVED_BUT_NOT_DOCUMENTED = Set.of(
            "/internal/rag/embeddings"
    );

    /** The repository's own ordering whitelist, read off its source. */
    private static final Path SEARCH_REPO = Path.of("src", "main", "java", "com", "careeros", "job",
            "repository", "JobSearchRepository.java");

    private static Set<String> orderings() {
        String source;
        try {
            source = Files.readString(SEARCH_REPO);
        } catch (IOException e) {
            throw new UncheckedIOException("expected the job search repository at "
                    + SEARCH_REPO.toAbsolutePath(), e);
        }
        int from = source.indexOf("ORDERINGS = Map.of(");
        if (from < 0) {
            throw new IllegalStateException("the ordering whitelist moved out of "
                    + "Map.of(...) form; this rule has to be rewritten with it");
        }
        String block = source.substring(from, source.indexOf(");", from));
        Set<String> keys = new TreeSet<>();
        Matcher pair = Pattern.compile("\"([a-z_]+)\", \"").matcher(block);
        while (pair.find()) {
            keys.add(pair.group(1));
        }
        return keys;
    }

    /** The sort values the doc lists after `sort=`, from the same cell. */
    private static Set<String> documentedSorts() {
        Set<String> out = new TreeSet<>();
        for (String line : lines()) {
            // greedy to the end of the run: the list stops at a comma or a backtick, not at the
            // last pipe -- `sort=a|b|c, page` must yield c as well as a and b. The pipes are
            // backslash-escaped in the table, so the escapes come back off before comparing.
            Matcher row = Pattern.compile("sort=([A-Za-z0-9_|\\\\]+)").matcher(line);
            while (row.find()) {
                for (String value : row.group(1).split("\\\\\\|")) {
                    if (!value.isBlank()) {
                        out.add(value.replace("\\", "").trim());
                    }
                }
            }
        }
        return out;
    }

    /**
     * `?sort=` is a name the reader picks and the repository maps to SQL, defaulting to `posted`
     * for anything it does not know -- so a value the doc advertises and the map lacks is not an
     * error, just a list that silently arrives in the wrong order.
     */
    @Test
    void everySortValueTheDocOffersIsOneTheRepositoryOrdersBy() {
        Set<String> offered = documentedSorts();
        assertThat(offered).as("the doc was read for sort values").hasSizeGreaterThanOrEqualTo(4);
        assertThat(new TreeSet<>(offered)).isEqualTo(orderings());
    }

    /** The client's own path map, which says it is the single source of truth for paths. */
    private static final Path CLIENT_ENDPOINTS =
            Path.of("..", "frontend", "src", "lib", "api", "endpoints.ts");

    /** Every path the browser can build: string literals and `${...}` templates alike. */
    private static Set<String> clientPaths() {
        Set<String> out = new TreeSet<>();
        String source;
        try {
            source = Files.readString(CLIENT_ENDPOINTS);
        } catch (IOException e) {
            throw new UncheckedIOException("expected the client's endpoint map at "
                    + CLIENT_ENDPOINTS.toAbsolutePath(), e);
        }
        // a path must open with a real segment: the module's own url() helper contains "/" and
        // `/${path}`, neither of which is an endpoint
        Matcher literal = Pattern.compile("\"(/[A-Za-z][^\"]*)\"").matcher(source);
        while (literal.find()) {
            out.add(documentedForm(literal.group(1)));
        }
        Matcher template = Pattern.compile("`(/[A-Za-z][^`]*)`").matcher(source);
        while (template.find()) {
            out.add(documentedForm(template.group(1).replaceAll("\\$\\{[^}]*}", "{}")));
        }
        out.remove("/api/v1");
        return out;
    }

    /**
     * The client's path map has its own guard, but that one compares against a hand-copied list of
     * what the backend serves -- so a route removed on this side keeps the client looking correct and
     * 404 at runtime. Here the same claim is checked against the mappings themselves.
     */
    @Test
    void everyPathTheClientBuildsIsOneSpringServes() {
        Set<String> served = new TreeSet<>();
        for (Route route : routes()) {
            served.add(route.path());
        }
        Set<String> callers = clientPaths();
        Set<String> orphans = new TreeSet<>(callers);
        orphans.removeAll(served);
        assertThat(orphans).as("client paths with no mapping behind them").isEqualTo(Set.of());
        assertThat(callers).as("the client map was read").hasSizeGreaterThanOrEqualTo(45);
    }
}
