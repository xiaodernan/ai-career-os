package com.careeros.knowledge.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.auth.security.InternalApiFilter;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.AuthUser;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.careeros.config.AppProperties;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.storage.StorageService;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The one route in this repository that answers with a file's bytes is the one route no test had
 * ever knocked on: {@code grep -rn internal/files backend/src/test} returned nothing before this
 * file existed, while {@code InternalFileController.java:53} is the only place in shipped code that
 * reads a media type out of a record and hands it to an HTTP answer (the shape gate's finding).
 * Its caller is the ingestion pipeline, which builds the URL in Python
 * ({@code app/ingestion/pipeline.py:24}) and then reads only {@code r.content} -- so the two things
 * that make this route work for that client, the raw byte body and the shared-token guard armed by
 * the same prefix string, had never been stated anywhere except in those two files.
 *
 * <p>Standalone setup installs the production advice, the production exception handler and a real
 * {@link InternalApiFilter} built the way {@code SecurityConfig} builds it, so a request travels the
 * same two decisions it travels in the running app: whether the prefix is guarded, and whether the
 * body is enveloped. Neither is stubbed here.
 */
class InternalFileControllerTest {

    private static final String TOKEN = "internal-token-under-test";
    private static final UUID OWNER = UUID.fromString("11111111-1111-4111-8111-111111111111");
    private static final UUID OTHER = UUID.fromString("22222222-2222-4222-8222-222222222222");
    private static final UUID BLOB = UUID.fromString("33333333-3333-4333-8333-333333333333");

    /** The exact key shape {@code ResumeService.persistUpload} writes: userId/resumes/uuid.ext. */
    private static final String KEY_PDF = OWNER + "/resumes/" + BLOB + ".pdf";
    private static final byte[] PDF_BYTES = "%PDF-1.4\n%cairo\n0 obj\n<<>>\nendobj\ntrailer\n"
            .getBytes(StandardCharsets.UTF_8);

    private static final Path MAIN = Path.of("src", "main");
    private static final Path CONTROLLER = MAIN.resolve(
            "java/com/careeros/knowledge/web/InternalFileController.java");
    private static final Path FILTER = MAIN.resolve("java/com/careeros/auth/security/InternalApiFilter.java");
    private static final Path SECURITY = MAIN.resolve("java/com/careeros/config/SecurityConfig.java");
    private static final Path FILE_INGEST = MAIN.resolve(
            "java/com/careeros/knowledge/service/FileIngestService.java");
    private static final Path RESUME_SERVICE = MAIN.resolve("java/com/careeros/resume/service/ResumeService.java");
    private static final Path KNOWLEDGE_SERVICE = MAIN.resolve(
            "java/com/careeros/knowledge/service/KnowledgeService.java");
    private static final Path CONFIG_YML = MAIN.resolve("resources/application.yml");
    private static final Path PIPELINE = Path.of("..", "ai-service", "app", "ingestion", "pipeline.py");

    /** The prefix the controller maps plus the slash it strips, read off its own source. */
    private static final String ROUTE = mapped() + "/";

    private DocumentRepository documents;
    private StorageService storage;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        documents = mock(DocumentRepository.class);
        storage = mock(StorageService.class);
        AppProperties props = new AppProperties();
        props.getInternal().setToken(TOKEN);
        mvc = MockMvcBuilders.standaloneSetup(new InternalFileController(documents, storage))
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .addFilters(new InternalApiFilter(props, new ObjectMapper()))
                .build();
    }

    @AfterEach
    void clearPrincipal() {
        SecurityContextHolder.clearContext();
    }

    private static Document document(String fileKey, String mediaType, UUID owner) {
        Document doc = new Document();
        doc.setUserId(owner);
        doc.setFileKey(fileKey);
        doc.setMediaType(mediaType);
        doc.setContentHash("0".repeat(64));
        doc.setStatus("indexing");
        return doc;
    }

    private void givenStored(String fileKey, String mediaType, UUID owner, byte[] bytes) {
        when(documents.findByFileKey(fileKey)).thenReturn(Optional.of(document(fileKey, mediaType, owner)));
        when(storage.getBytes(fileKey)).thenReturn(bytes);
    }

    /**
     * The route reads exactly one string — {@code request.getRequestURI()} — and half the URIs below
     * are deliberately not legal URLs. The template form of {@code get(...)} cannot carry them: it
     * builds a {@code java.net.URI} on the way, which percent-encodes what it finds (so {@code %zz}
     * would arrive as {@code %25zz}, a different input) or throws before the request exists (measured:
     * {@code get("...%zz")} throws at builder construction). Installing the raw URI on the built
     * request tests the string the controller actually reads, with nothing between the two.
     */
    private static MockHttpServletRequestBuilder internal(String requestUri) {
        return get("/").with(request -> {
            request.setRequestURI(requestUri);
            return request;
        }).header("X-Internal-Token", TOKEN);
    }

    private static MockHttpServletRequestBuilder anonymous(String requestUri) {
        return get("/").with(request -> {
            request.setRequestURI(requestUri);
            return request;
        });
    }

    // ------------------------------------------------------------ the path the ingestion client uses

    @Test
    void the_url_the_ingestion_client_builds_answers_with_the_stored_bytes() throws Exception {
        givenStored(KEY_PDF, "application/pdf", OWNER, PDF_BYTES);

        mvc.perform(internal(ROUTE + KEY_PDF))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/pdf"))
                .andExpect(content().bytes(PDF_BYTES));
    }

    @Test
    void the_body_is_the_file_itself_because_the_envelope_advice_steps_aside_for_a_byte_array()
            throws Exception {
        // EnvelopeAdvice wraps every controller return value except the four shapes it names, and
        // `byte[]` is one of them. That exemption is why `_fetch_bytes` can hand `r.content` straight
        // to `extract_text`, whose first branch looks for the literal `%PDF-` at offset 0. Take the
        // exemption away and the answer is not a wrapped PDF — it is no answer at all: the method's
        // declared `ResponseEntity<byte[]>` makes Spring choose ByteArrayHttpMessageConverter, which
        // casts the envelope body to `[B and throws ClassCastException, so every download in the
        // system 500s before a byte of the bucket reaches the caller.
        givenStored(KEY_PDF, "application/pdf", OWNER, PDF_BYTES);

        MvcResult result = mvc.perform(internal(ROUTE + KEY_PDF)).andExpect(status().isOk()).andReturn();

        byte[] body = result.getResponse().getContentAsByteArray();
        assertThat(body).isEqualTo(PDF_BYTES);
        assertThat(new String(body, StandardCharsets.UTF_8)).doesNotStartWith("{");
        assertThat(new String(body, StandardCharsets.UTF_8)).startsWith("%PDF-");
        assertThat(result.getResponse().getContentType()).doesNotContain("json");
    }

    @Test
    void the_key_is_the_whole_tail_of_the_url_and_reaches_the_lookup_and_the_bucket_unchanged()
            throws Exception {
        givenStored(KEY_PDF, "application/pdf", OWNER, PDF_BYTES);

        mvc.perform(internal(ROUTE + KEY_PDF)).andExpect(status().isOk());

        ArgumentCaptor<String> looked = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> fetched = ArgumentCaptor.forClass(String.class);
        verify(documents).findByFileKey(looked.capture());
        verify(storage).getBytes(fetched.capture());

        assertThat(looked.getValue()).isEqualTo(KEY_PDF);
        assertThat(fetched.getValue()).isEqualTo(looked.getValue());
        // The tail is three segments, so a route that kept only the last path segment -- or only the
        // first -- would ask both places for a key that no row holds.
        String lastSegment = looked.getValue().substring(looked.getValue().lastIndexOf('/') + 1);
        assertThat(looked.getValue()).isNotEqualTo(lastSegment);
        assertThat(looked.getValue()).startsWith(OWNER + "/resumes/");
    }

    @Test
    void the_media_type_in_the_answer_is_the_column_and_never_the_extension() throws Exception {
        // The key says pdf, the row says text/plain, and the answer follows the row, because the row
        // is the only media-type read this route has -- and it is the same column the Python parser
        // dispatch reads, so the two consumers of one upload cannot disagree about the type.
        givenStored(KEY_PDF, "text/plain", OWNER, "just words\n".getBytes(StandardCharsets.UTF_8));

        mvc.perform(internal(ROUTE + KEY_PDF))
                .andExpect(status().isOk())
                .andExpect(content().contentType("text/plain"));

        reset(documents, storage);
        String docxKey = OWNER + "/knowledge/" + BLOB + ".docx";
        givenStored(docxKey, "application/pdf", OWNER, PDF_BYTES);

        mvc.perform(internal(ROUTE + docxKey))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/pdf"))
                .andExpect(content().bytes(PDF_BYTES));
    }

    // ------------------------------------------------------------ the key shape, in both directions

    @Test
    void every_extension_an_upload_author_can_write_is_served_and_the_two_folder_spellings_are_pinned()
            throws Exception {
        List<String> extensions = writtenExtensions();
        // The two authors, and the literals each one pastes into the key it builds.
        assertThat(reads(RESUME_SERVICE)).contains("userId + \"/resumes/\"");
        assertThat(reads(FILE_INGEST)).contains("userId + \"/\" + folder + \"/\"");
        assertThat(reads(KNOWLEDGE_SERVICE)).contains("String folder = \"knowledge\"");

        for (String folder : List.of("resumes", "knowledge")) {
            for (String ext : extensions) {
                String key = OWNER + "/" + folder + "/" + BLOB + "." + ext;
                givenStored(key, "application/octet-stream", OWNER, PDF_BYTES);

                mvc.perform(internal(ROUTE + key))
                        .andExpect(status().isOk())
                        .andExpect(content().bytes(PDF_BYTES));
            }
        }
        assertThat(extensions).hasSize(3);
    }

    @Test
    void a_key_shaped_like_an_upload_but_not_quite_is_refused_before_anything_is_read() throws Exception {
        String thirtyFive = BLOB.toString().substring(0, 35);
        List<String> nearMisses = List.of(
                OWNER + "/notes/" + BLOB + ".pdf",          // a folder no author writes
                OWNER + "/knowledge/" + BLOB + ".doc",      // a fourth extension
                OWNER + "/knowledge/" + BLOB + ".PDF",      // the alternation is lower case
                OWNER + "/knowledge/" + thirtyFive + ".txt", // one character short of 36
                OWNER + "/knowledge/" + BLOB + "x.txt",     // one character long
                OWNER + "/knowledge/" + BLOB,               // no extension at all
                BLOB + ".pdf");                              // no folder segment at all

        for (String key : nearMisses) {
            mvc.perform(internal(ROUTE + key))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.error.code").value("FILE_KEY_INVALID"))
                    .andExpect(jsonPath("$.error.message").value("Invalid file key format"));
        }
        // None of them reached the repository, so none of them could probe which keys exist.
        verifyNoInteractions(documents, storage);
    }

    @Test
    void a_request_that_names_no_key_is_refused_rather_than_indexing_past_the_prefix() throws Exception {
        // `full.substring(Math.min(prefix.length(), full.length()))` is the only thing keeping a
        // request shorter than the prefix from throwing StringIndexOutOfBounds, which the catch-all
        // would hand back as a 500 for what is nothing more than a bad URL.
        mvc.perform(internal(ROUTE))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message").value("Invalid file key format"));

        mvc.perform(internal(ROUTE.substring(0, ROUTE.length() - 1)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message").value("Invalid file key format"));

        verifyNoInteractions(documents, storage);
    }

    // ------------------------------------------------------------ decode, then check, then look up

    @Test
    void a_malformed_percent_escape_is_refused_by_the_framework_before_the_route_sees_it() throws Exception {
        // The route's own decode catch (InternalFileController.java:41-45) looks like the thing that
        // answers `%zz`. It is not reachable from HTTP: Spring parses and decodes the request path
        // while it is still mapping the request, so the IllegalArgumentException surfaces there —
        // before any handler, and therefore before @RestControllerAdvice can envelope it. What the
        // caller gets is a throw, not the 400 the catch was written to produce.
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI(ROUTE + OWNER + "/resumes/%zz");

        assertThatThrownBy(() -> mvc.perform(internal(ROUTE + OWNER + "/resumes/%zz")))
                .rootCause()
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("%zz");

        // Nothing was read, because nothing ran.
        verifyNoInteractions(documents, storage);
        // And the branch the framework outran does work when handed the request directly.
        ApiException ex = assertThrows(ApiException.class,
                () -> new InternalFileController(documents, storage).get(request));
        assertThat(ex.code()).isEqualTo(ApiErrorCode.FILE_KEY_MALFORMED);
        assertThat(ex).hasMessage("Malformed file key");
    }

    @Test
    void an_encoded_traversal_is_refused_and_never_reaches_the_repository_or_the_bucket()
            throws Exception {
        // Three spellings that all stop at the same line. Which clause of the guard fires cannot be
        // told from the answer -- the `..` test, the `\` test and the shape regex all throw the same
        // code and message -- so what this case pins is the refusal and the absence of any read, not
        // a claim about the clause. Measured, that is the right claim to make: deleting both string
        // tests changes nothing in this class, because FILE_KEY admits no `.` beyond the one literal
        // dot before the extension and no backslash anywhere, so the shape regex refuses every one of
        // these inputs on its own.
        mvc.perform(internal(ROUTE + "%2e%2e/%2e%2e/%2e%2e/etc/passwd"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message").value("Invalid file key format"));

        mvc.perform(internal(ROUTE + "../../../etc/passwd"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message").value("Invalid file key format"));

        // The backslash spelling carries both sequences, so it joins the other two in the same
        // refusal; nothing here can tell the reader which clause of the guard was the reason.
        mvc.perform(internal(ROUTE + OWNER + "/resumes/..\\..\\web.xml"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error.message").value("Invalid file key format"));

        verifyNoInteractions(documents, storage);
    }

    @Test
    void a_url_encoded_slash_becomes_a_key_separator_because_the_decode_sits_above_the_shape_check()
            throws Exception {
        // The one ordering this route has: decode, then check, then look up. Spring hands over
        // getRequestURI() raw, so `%2f` arrives as three characters; the decode turns them into the
        // separator the key format requires, and the repository is then asked for a key the URL never
        // spelled. Checking the raw form first -- the order the file does NOT use -- answers 400 here.
        String encodedKey = OWNER + "%2fresumes%2f" + BLOB + ".pdf";
        givenStored(KEY_PDF, "application/pdf", OWNER, PDF_BYTES);

        mvc.perform(internal(ROUTE + encodedKey))
                .andExpect(status().isOk())
                .andExpect(content().bytes(PDF_BYTES));

        ArgumentCaptor<String> looked = ArgumentCaptor.forClass(String.class);
        verify(documents).findByFileKey(looked.capture());
        assertThat(looked.getValue()).isEqualTo(KEY_PDF).isNotEqualTo(encodedKey);
    }

    @Test
    void a_key_no_document_owns_answers_document_not_found_without_opening_the_bucket() throws Exception {
        when(documents.findByFileKey(KEY_PDF)).thenReturn(Optional.empty());

        mvc.perform(internal(ROUTE + KEY_PDF))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("DOCUMENT_NOT_FOUND"))
                .andExpect(jsonPath("$.error.message").value("No document owns this key"));

        // The row is consulted first, so an unknown key costs a query and not an object fetch.
        verifyNoInteractions(storage);
    }

    // ------------------------------------------------------------ who arms the route, and who does not

    @Test
    void a_request_without_the_internal_token_is_refused_by_the_filter_that_names_itself() throws Exception {
        givenStored(KEY_PDF, "application/pdf", OWNER, PDF_BYTES);

        mvc.perform(anonymous(ROUTE + KEY_PDF))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("UNAUTHORIZED"))
                // SecurityConfig's entry point says "Authentication required" and InternalApiFilter
                // says "Invalid internal token"; the message is what tells the caller which of the
                // two gates refused it, so the refusal has to stay attributable to its own filter.
                .andExpect(jsonPath("$.error.message").value("Invalid internal token"));

        mvc.perform(anonymous(ROUTE + KEY_PDF).header("X-Internal-Token", "not-" + TOKEN))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.message").value("Invalid internal token"));

        verifyNoInteractions(documents, storage);
    }

    @Test
    void a_document_owned_by_someone_else_is_served_because_the_route_scopes_by_nobody() throws Exception {
        // Characterization, not approval. This route has no user in its signature and no owner check
        // in its body, and SecurityConfig permits /api/internal/** so the JWT chain never runs:
        // anyone holding the shared service token reads any user's uploaded bytes. Turning that into
        // a per-user check is a live authorisation change, so this case only states the shipped fact.
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(OWNER, "ada@example.invalid", "user"), null, List.of()));
        givenStored(KEY_PDF, "application/pdf", OTHER, PDF_BYTES);

        mvc.perform(internal(ROUTE + KEY_PDF)).andExpect(status().isOk());

        // The repository does have a user-scoped finder. This route does not call it.
        verify(documents, never()).findByIdAndUserId(any(), any());
        verify(documents).findByFileKey(KEY_PDF);
    }

    @Test
    void every_spelling_of_the_internal_prefix_is_one_string_and_the_shipped_config_adds_no_context_path()
            throws Exception {
        String mapped = mapped();
        // The prefix the controller strips is the mapping plus a slash, written out a second time.
        assertThat(apiLiterals(CONTROLLER)).containsExactlyInAnyOrder(mapped, mapped + "/");
        assertThat(reads(CONTROLLER)).contains("request.getContextPath() + \"" + mapped + "/\"");
        // The guard fires on a shorter prefix of the same string, which is why a renamed or
        // deepened mapping stops being guarded instead of failing loudly.
        List<String> guarded = apiLiterals(FILTER);
        assertThat(guarded).hasSize(1);
        assertThat(mapped).startsWith(guarded.get(0));
        assertThat(reads(FILTER)).contains("startsWith(\"" + guarded.get(0) + "\")");
        // Spring Security lets the whole guarded surface through unauthenticated. It is spelled from
        // the guard's prefix, NOT from this controller's mapping: the shipped matcher list is
        // /api/v1/auth/**, /api/v1/health and /api/internal/**, and no entry names /api/internal/files.
        // So the fact that keeps this route open to a bearer-less caller is one string shared with
        // every other internal endpoint — a second route deeper than the guard's prefix would be let
        // through by the same line and then go unguarded by the filter, silently.
        assertThat(apiLiterals(SECURITY)).contains(guarded.get(0) + "/**");
        assertThat(apiLiterals(SECURITY)).doesNotContain(mapped + "/**");
        // And the Python client builds its URL from the mapped prefix plus one slash.
        assertThat(reads(PIPELINE)).contains("backend_base_url}" + ROUTE + "{file_key}");
        // The strip only agrees with that URL while nothing is configured in front of the app.
        assertThat(reads(CONFIG_YML)).doesNotContain("context-path");
        assertThat(ROUTE).isEqualTo(mapped + "/");
    }

    // ------------------------------------------------------------ measurement helpers

    private static String mapped() {
        Matcher m = Pattern.compile("@RequestMapping\\(\"([^\"]+)\"\\)").matcher(reads(CONTROLLER));
        if (!m.find()) {
            throw new IllegalStateException("expected the download controller to map its route with "
                    + "@RequestMapping(\"/...\") and found no such annotation in " + CONTROLLER);
        }
        String value = m.group(1);
        if (m.find()) {
            throw new IllegalStateException("expected exactly one @RequestMapping on the download route, "
                    + "found a second one in " + CONTROLLER);
        }
        return value;
    }

    /** Every {@code "...."} literal in a Java source that opens a path under /api/. */
    private static List<String> apiLiterals(Path source) {
        List<String> out = new ArrayList<>();
        Matcher m = Pattern.compile("\"(/api/[^\"]*)\"").matcher(reads(source));
        while (m.find()) {
            out.add(m.group(1));
        }
        assertThat(out).as("the /api/ path literals written in %s", source).isNotEmpty();
        return out;
    }

    /** The extensions {@code FileIngestService.keyFor} can put on a key, off its own switch. */
    private static List<String> writtenExtensions() {
        List<String> out = new ArrayList<>();
        Matcher m = Pattern.compile("case [A-Z_]+ -> \"([a-z0-9]+)\";").matcher(reads(FILE_INGEST));
        while (m.find()) {
            out.add(m.group(1));
        }
        assertThat(out).as("the extension switch in %s", FILE_INGEST).isNotEmpty();
        return out;
    }

    private static String reads(Path file) {
        if (!Files.isRegularFile(file)) {
            throw new IllegalStateException("expected " + file + " under the module directory, found "
                    + Path.of("").toAbsolutePath());
        }
        try {
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("could not read " + file, e);
        }
    }
}
