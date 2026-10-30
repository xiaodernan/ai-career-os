package com.careeros.report.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.repository.GrowthPlanRepository;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.UserProfile;
import com.careeros.conversation.entity.Conversation;
import com.careeros.conversation.entity.Message;
import com.careeros.conversation.repository.ConversationRepository;
import com.careeros.conversation.repository.MessageRepository;
import com.careeros.report.service.ExportService;
import com.careeros.report.service.ImportService;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.knowledge.repository.UserNoteRepository;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.dto.KnowledgeDtos.NoteRequest;
import com.careeros.knowledge.service.KnowledgeService;
import com.careeros.interview.entity.InterviewEvaluation;
import com.careeros.interview.entity.InterviewSession;
import com.careeros.interview.entity.InterviewTurn;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.interview.repository.InterviewTurnRepository;
import com.careeros.job.entity.JobJd;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.network.repository.ContactRepository;
import com.careeros.network.entity.Contact;
import com.careeros.network.service.ContactService;
import com.careeros.resume.service.ResumeService;
import com.careeros.common.AuthUser;
import com.careeros.common.CurrentUserArgumentResolver;
import com.careeros.common.EnvelopeAdvice;
import com.careeros.common.GlobalExceptionHandler;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * The data-portability routes (Epics 13.1-13.3).
 *
 * <p>The bundle is the user's own data, so two things are worth pinning: the
 * export is scoped to the caller and its anonymized flag reaches the engine as
 * the boolean it is (not as a truthy string), and the redaction route passes
 * the sections to drop through untouched — a name the engine does not know is
 * the engine's to refuse, not the bridge's to swallow.
 */
class DataPortabilityControllerTest {

    private static final String USER = "6b0178a0-d352-09c3-ea65-8f107bd28d01";

    private final ObjectMapper objectMapper = new ObjectMapper();

    private AiServiceClient ai;
    private ApplicationRepository applications;
    private GrowthPlanRepository growthPlans;
    private UserProfileRepository profiles;
    private UserNoteRepository notes;
    private ContactRepository contacts;
    private KnowledgeService knowledge;
    private ContactService contactService;
    private JobJdRepository jds;
    private InterviewSessionRepository sessions;
    private InterviewTurnRepository turns;
    private InterviewEvaluationRepository evaluations;
    private ConversationRepository conversations;
    private MessageRepository messages;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        applications = mock(ApplicationRepository.class);
        growthPlans = mock(GrowthPlanRepository.class);
        profiles = mock(UserProfileRepository.class);
        notes = mock(UserNoteRepository.class);
        contacts = mock(ContactRepository.class);
        knowledge = mock(KnowledgeService.class);
        contactService = mock(ContactService.class);
        jds = mock(JobJdRepository.class);
        sessions = mock(InterviewSessionRepository.class);
        turns = mock(InterviewTurnRepository.class);
        evaluations = mock(InterviewEvaluationRepository.class);
        conversations = mock(ConversationRepository.class);
        messages = mock(MessageRepository.class);
        when(conversations.findByUserIdOrderByUpdatedAtDescIdAsc(
                eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        ExportService exports = new ExportService(ai, applications, growthPlans,
                notes, contacts, conversations, messages);
        ImportService imports = new ImportService(ai, exports, profiles, notes,
                contacts, applications, growthPlans,
                mock(ResumeService.class), knowledge, contactService,
                jds, mock(JobRepository.class),
                sessions, turns, evaluations, conversations, messages);
        DataPortabilityController controller = new DataPortabilityController(ai, exports, imports);
        mvc = MockMvcBuilders.standaloneSetup(controller)
                .setControllerAdvice(new EnvelopeAdvice(), new GlobalExceptionHandler())
                .setCustomArgumentResolvers(new CurrentUserArgumentResolver())
                .build();
        SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(
                new AuthUser(UUID.fromString(USER), "ada@example.invalid", "user"), null, List.of()));
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    /**
     * {@code id} is {@code @UuidGenerator}-managed, so a detached chat or
     * message gets the value the persistence layer would assign by reflection.
     */
    private static void identify(Object target, UUID id) {
        try {
            java.lang.reflect.Field f = target.getClass().getDeclaredField("id");
            f.setAccessible(true);
            f.set(target, id);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("cannot set id", e);
        }
    }

    /**
     * The backend-owned half of the current state, empty.
     *
     * <p>The apply reads it before it executes the plan, and a Mockito page
     * is {@code null} until it is told otherwise.
     */
    private void stubAnEmptyWorkspace() {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(
                eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
    }

    @Test
    void the_export_is_the_engines_bundle_wrapped_once() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.exportBundle(eq(UUID.fromString(USER)), anyBoolean(), any()))
                .thenReturn(Map.of("schema_version", "1.1.0",
                        "manifest", Map.of("content_hash", "abc123")));

        mvc.perform(post("/api/v1/data-portability/export")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.schema_version").value("1.1.0"))
                .andExpect(jsonPath("$.data.manifest.content_hash").value("abc123"));

        verify(ai).exportBundle(eq(UUID.fromString(USER)), eq(false), any());
    }

    /**
     * The render route hands the caller's format straight to the engine.
     *
     * <p>The Markdown half of a bundle used to be a library function nothing
     * called -- the route served the HTML and the PDF, so the operator's quick
     * look existed only for someone already inside Python. The format now
     * travels the wire like the other two, and the bridge does not get to
     * decide which one the caller meant.
     */
    @Test
    void the_render_route_hands_the_callers_format_to_the_engine() throws Exception {
        when(ai.renderBundle(eq(UUID.fromString(USER)), any(), eq("markdown"), isNull()))
                .thenReturn(Map.of("format", "markdown", "markdown", "# AI Career OS"));

        mvc.perform(post("/api/v1/data-portability/render")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\": {}, \"format\": \"markdown\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.format").value("markdown"))
                .andExpect(jsonPath("$.data.markdown").value("# AI Career OS"));

        verify(ai).renderBundle(eq(UUID.fromString(USER)), any(), eq("markdown"), isNull());
    }

    /**
     * The bundle is complete: the sections the BACKEND owns travel with it, so
     * an export is the candidate's pipeline and not only their reading list.
     *
     * <p>And the two the reader typed into travel too -- their notes and the
     * people they know. They are the first things a reader loses when they
     * leave, because the bundle used to carry every table the *engines* read
     * and neither table the reader wrote in.
     */
    @Test
    void the_export_carries_the_sections_the_backend_owns() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());

        UserNote note = new UserNote();
        note.setUserId(UUID.fromString(USER));
        note.setTitle("Salary research");
        note.setContent("Hangzhou senior backend, 40-60w total.");
        when(notes.findByUserId(eq(UUID.fromString(USER)))).thenReturn(List.of(note));

        Contact contact = new Contact();
        contact.setUserId(UUID.fromString(USER));
        contact.setName("Li Ming");
        contact.setCompany("Acme");
        contact.setRelation("Mentor");
        contact.setNotes("Met at the conference; happy to review my design.");
        when(contacts.findByUserIdOrderByUpdatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of(contact));

        UUID chatId = UUID.fromString("99999999-9999-9999-9999-999999999999");
        Conversation chat = new Conversation();
        identify(chat, chatId);
        chat.setUserId(UUID.fromString(USER));
        chat.setTitle("Which resume fits a platform role?");
        chat.setContext(Map.of("resumeId", "r1"));
        Message answer = new Message();
        identify(answer, UUID.fromString("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"));
        answer.setConversationId(chatId);
        answer.setUserId(UUID.fromString(USER));
        answer.setRole("assistant");
        answer.setContent("The platform resume, because the posting leads with scale.");
        answer.setArtifacts(List.of(Map.of("kind", "resume", "version", 2)));
        when(conversations.findByUserIdOrderByUpdatedAtDescIdAsc(
                eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(chat)));
        when(messages.findByConversationIdInOrderByCreatedAtAscIdAsc(List.of(chatId)))
                .thenReturn(List.of(answer));

        when(ai.exportBundle(eq(UUID.fromString(USER)), anyBoolean(), any()))
                .thenReturn(Map.of("schema_version", "1.3.0"));

        mvc.perform(post("/api/v1/data-portability/export")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isOk());

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> sections = ArgumentCaptor.forClass(Map.class);
        verify(ai).exportBundle(eq(UUID.fromString(USER)), eq(false), sections.capture());
        assertThat(sections.getValue()).containsKeys(
                "applications", "growth_plans", "notes", "contacts", "conversations");

        // And the reader's own words are in there, not just the section names.
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> exportedNotes =
                (List<Map<String, Object>>) sections.getValue().get("notes");
        assertThat(exportedNotes).hasSize(1);
        assertThat(exportedNotes.get(0))
                .containsEntry("title", "Salary research")
                .containsEntry("content", "Hangzhou senior backend, 40-60w total.");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> exportedContacts =
                (List<Map<String, Object>>) sections.getValue().get("contacts");
        assertThat(exportedContacts).hasSize(1);
        assertThat(exportedContacts.get(0))
                .containsEntry("name", "Li Ming")
                .containsEntry("relation", "Mentor")
                .containsEntry("notes", "Met at the conference; happy to review my design.");

        // The chats travel with their transcripts: a bundle that leaves them
        // out loses the reasoning behind the resumes and plans it does carry.
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> exportedChats =
                (List<Map<String, Object>>) sections.getValue().get("conversations");
        assertThat(exportedChats).hasSize(1);
        assertThat(exportedChats.get(0))
                .containsEntry("title", "Which resume fits a platform role?")
                .containsKey("context");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> transcript =
                (List<Map<String, Object>>) exportedChats.get(0).get("messages");
        assertThat(transcript).hasSize(1);
        assertThat(transcript.get(0))
                .containsEntry("role", "assistant")
                .containsEntry("content",
                        "The platform resume, because the posting leads with scale.")
                .doesNotContainKey("agent_run_id");
    }

    /**
     * A restore into another account does not write over the source's rows.
     *
     * <p>The bundle's ids are the source's, and the restore keeps them so the
     * links inside the bundle still point where they did. But an id that
     * belongs to <em>another</em> account's row must not be written into: the
     * caller's restore would change somebody else's data, and the caller
     * would get nothing of their own -- while the answer said "created".
     *
     * <p>So the id is kept when it is free and minted when it is not. This
     * is the share case, and it is the one the export is advertised for.
     */
    @Test
    void a_restore_into_another_account_does_not_write_over_the_source() throws Exception {
        UUID sourceId = UUID.fromString("11111111-1111-1111-1111-111111111111");
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("notes", List.of(
                        Map.of("op", "create", "id", sourceId.toString())))));
        // The caller does not have that note ...
        when(notes.findByIdAndUserId(eq(sourceId), eq(UUID.fromString(USER))))
                .thenReturn(Optional.empty());
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());

        Map<String, Object> bundle = Map.of(
                "schema_version", "1.2.0",
                "data", Map.of("notes", List.of(
                        Map.of("id", sourceId.toString(),
                                "title", "Someone else's note",
                                "content", "not the caller's to change"))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("bundle", bundle))))
                .andExpect(status().isOk());

        // The row that was written is the caller's own: the knowledge service
        // authored it, with an id of its own, and nobody else's row was
        // touched.
        @SuppressWarnings("unchecked")
        ArgumentCaptor<NoteRequest> written = ArgumentCaptor.forClass(NoteRequest.class);
        verify(knowledge).createNote(eq(UUID.fromString(USER)), written.capture());
        assertThat(written.getValue().content()).isEqualTo("not the caller's to change");
        verify(knowledge, never()).deleteNote(any(), any());
    }

    @Test
    void the_anonymized_flag_reaches_the_engine_as_a_boolean() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.exportBundle(eq(UUID.fromString(USER)), anyBoolean(), any()))
                .thenReturn(Map.of("schema_version", "1.1.0"));

        mvc.perform(post("/api/v1/data-portability/export")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"anonymized\":true}"))
                .andExpect(status().isOk());

        verify(ai).exportBundle(eq(UUID.fromString(USER)), eq(true), any());
    }

    @Test
    void the_import_plan_carries_the_bundle_and_the_existing_state() throws Exception {
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("op_counts", Map.of("create", 1, "update", 2, "delete", 0, "total", 3)));

        mvc.perform(post("/api/v1/data-portability/import-plan")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.0.0"},
                                 "existing":{"schema_version":"1.0.0"}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.op_counts.total").value(3));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> bundle = ArgumentCaptor.forClass(Map.class);
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> existing = ArgumentCaptor.forClass(Map.class);
        verify(ai).importPlan(eq(UUID.fromString(USER)), bundle.capture(), existing.capture());
        assertThat(bundle.getValue()).containsKey("schema_version");
        assertThat(existing.getValue()).containsKey("schema_version");
    }

    @Test
    void the_redaction_passes_the_sections_to_drop_through() throws Exception {
        when(ai.redactBundle(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("manifest", Map.of("redacted_sections", List.of("interviews"))));

        mvc.perform(post("/api/v1/data-portability/redact")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.0.0\"},\"drop\":[\"interviews\"]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.manifest.redacted_sections[0]").value("interviews"));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<String>> drop = ArgumentCaptor.forClass(List.class);
        verify(ai).redactBundle(eq(UUID.fromString(USER)), any(), drop.capture());
        assertThat(drop.getValue()).containsExactly("interviews");
    }

    /**
     * A redaction with no sections named is not an error: the caller asked for
     * nothing to be dropped, and the answer is the bundle unchanged.
     */
    @Test
    void a_redaction_with_nothing_to_drop_is_not_an_error() throws Exception {
        when(ai.redactBundle(eq(UUID.fromString(USER)), any(), isNull()))
                .thenReturn(Map.of("schema_version", "1.0.0"));

        mvc.perform(post("/api/v1/data-portability/redact")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.0.0\"}}"))
                .andExpect(status().isOk());

        verify(ai).redactBundle(eq(UUID.fromString(USER)), any(), isNull());
    }

    /**
     * The apply is the write half of the restore: it says what it wrote and
     * which sections it left alone, so a partial restore is visible rather
     * than reported as a success.
     */
    @Test
    void the_apply_reports_what_it_wrote_and_what_it_skipped() throws Exception {
        when(profiles.findByUserId(eq(UUID.fromString(USER)))).thenReturn(java.util.Optional.empty());
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of(
                        "op_counts", Map.of("create", 1, "update", 0, "delete", 0, "total", 1),
                        "sections", Map.of(
                                "profile", List.of(Map.of("op", "update", "id", "p1")),
                                // A section the plan names but the bundle does not
                                // carry the rows for: the apply cannot write what
                                // is not there, and it says so.
                                "interviews", List.of(Map.of("op", "create", "id", "i1")))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.1.0","data":{
                                  "profile":{"headline":"Backend engineer"}}}}
                                """))
                .andExpect(status().isOk())
                // The profile was written; the interviews were not, and the answer
                // says so rather than claiming the whole bundle landed.
                .andExpect(jsonPath("$.data.applied.profile.updated").value(1))
                .andExpect(jsonPath("$.data.skipped[0].section").value("interviews"));
    }

    /**
     * An unchanged row is not written, and the answer says so.
     *
     * <p>The panel's copy promises that "unchanged rows are skipped". The plan
     * is where that is decided, and this is where it has to be kept: a skip op
     * that the apply ignored would write the row again and report it as an
     * update, which is the half of the promise that used to be missing.
     */
    @Test
    void an_unchanged_row_is_not_written_again() throws Exception {
        UUID noteId = UUID.fromString("22222222-2222-2222-2222-222222222222");
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(
                eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of(
                        "op_counts", Map.of("create", 0, "update", 0, "delete", 0,
                                "skip", 1, "total", 1),
                        "sections", Map.of("notes", List.of(
                                Map.of("op", "skip", "id", noteId.toString(),
                                        "content_hash", "same-hash")))));

        Map<String, Object> bundle = Map.of(
                "schema_version", "1.2.0",
                "data", Map.of("notes", List.of(
                        Map.of("id", noteId.toString(), "title", "Salary research",
                                "content", "Hangzhou senior backend, 40-60w total."))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("bundle", bundle))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.notes.unchanged").value(1))
                .andExpect(jsonPath("$.data.applied.notes.created").value(0))
                .andExpect(jsonPath("$.data.applied.notes.updated").value(0));

        // Nothing was written: not a second copy, not an update, not a delete.
        verify(knowledge, never()).createNote(any(), any());
        verify(knowledge, never()).updateNote(any(), any(), any());
        verify(knowledge, never()).deleteNote(any(), any());
    }

    /**
     * The plan's {@code existing} half is the bundle's own serialization.
     *
     * <p>A skip is decided by comparing the bundle's row with the target's,
     * so a row summarized into three columns is a row the plan can never call
     * unchanged -- it would plan an update for a row nobody changed. And the
     * profile used to travel as the entity itself, whose field names are
     * camelCase, while the bundle's profile is the engine's snake_case
     * {@code SELECT *}. Both are pinned here, because either one alone turns
     * every re-import into a write.
     */
    @Test
    void the_existing_state_is_the_same_serialization_as_the_bundle() throws Exception {
        Application application = new Application();
        application.setUserId(UUID.fromString(USER));
        application.setTitle("Senior Backend Engineer");
        application.setCompanyName("Acme");
        application.setStatus("interviewing");
        application.setNotes("Phone screen went well.");
        application.setAppliedAt(java.time.OffsetDateTime.parse("2026-09-01T09:00:00Z"));
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(
                eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application)));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());

        UserProfile profile = new UserProfile();
        profile.setUserId(UUID.fromString(USER));
        profile.setHeadline("Backend engineer");
        profile.setYearsExperience(new java.math.BigDecimal("6.5"));
        when(profiles.findByUserId(eq(UUID.fromString(USER))))
                .thenReturn(Optional.of(profile));

        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of()));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.2.0\",\"data\":{}}}"))
                .andExpect(status().isOk());

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> existing = ArgumentCaptor.forClass(Map.class);
        verify(ai).importPlan(eq(UUID.fromString(USER)), any(), existing.capture());
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) existing.getValue().get("data");

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> rows = (List<Map<String, Object>>) data.get("applications");
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0))
                .containsEntry("title", "Senior Backend Engineer")
                .containsEntry("company_name", "Acme")
                .containsEntry("status", "interviewing")
                .containsEntry("notes", "Phone screen went well.")
                .containsKey("applied_at");

        @SuppressWarnings("unchecked")
        Map<String, Object> profileRow = (Map<String, Object>) data.get("profile");
        assertThat(profileRow)
                .containsEntry("headline", "Backend engineer")
                .containsKey("years_experience")
                .doesNotContainKey("yearsExperience");
    }

    /**
     * A bundle with no data section is not a bundle: the route refuses it
     * before the plan runs.
     */
    @Test
    void an_apply_without_a_data_section_is_refused() throws Exception {
        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.1.0\"}}"))
                .andExpect(status().isBadRequest());
    }

    /**
     * A bundle written before the export decoded its JSON columns still
     * restores them.
     *
     * <p>The bundle carries a {@code jsonb} column as the object it holds now;
     * before that it carried the column as its text, which is asyncpg's own
     * return shape passed straight through. Both are the same value written by
     * two versions of the product, and a restore that kept the text as a value
     * would look like it worked while the analyst's reading of the posting was
     * gone -- the row would come back with the raw text and nothing read out
     * of it.
     */
    @Test
    void a_bundle_from_an_older_export_restores_its_json_columns() throws Exception {
        when(profiles.findByUserId(eq(UUID.fromString(USER)))).thenReturn(Optional.empty());
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("job_descriptions", List.of(
                                Map.of("op", "create", "id", "22222222-2222-2222-2222-222222222222"))),
                        "op_counts", Map.of("create", 1, "update", 0, "delete", 0, "skip", 0, "total", 1)));

        Map<String, Object> bundle = Map.of(
                "schema_version", "1.2.0",
                "data", Map.of("job_descriptions", List.of(Map.of(
                        "id", "22222222-2222-2222-2222-222222222222",
                        "raw_text", "We are hiring backend engineers.",
                        "parsed", "{\"title\": \"Backend Engineer\", \"skills\": [\"java\"]}"))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of("bundle", bundle))))
                .andExpect(status().isOk());

        ArgumentCaptor<JobJd> written = ArgumentCaptor.forClass(JobJd.class);
        verify(jds).save(written.capture());
        assertThat(written.getValue().getParsed())
                .containsEntry("title", "Backend Engineer")
                .containsKey("skills");
    }

    /**
     * The restore's delete semantics for the sections it can name.
     *
     * <p>The plan compares the bundle with the reader's current state, so a
     * row the bundle no longer carries is a row the reader took out of the
     * document they asked to restore. The postings and the interviews are
     * those sections: their rows are matched by id, so the apply can retire
     * one -- and an interview is retired whole, because the transcript and
     * the report hang off the session.
     */
    @Test
    void a_retired_posting_is_deleted() throws Exception {
        stubAnEmptyWorkspace();
        UUID jdId = UUID.fromString("44444444-4444-4444-4444-444444444444");
        JobJd jd = new JobJd();
        when(jds.findByIdAndUserId(eq(jdId), eq(UUID.fromString(USER))))
                .thenReturn(Optional.of(jd));
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("job_descriptions", List.of(
                        Map.of("op", "delete", "id", jdId.toString())))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.2.0","data":{
                                  "job_descriptions":[]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.job_descriptions.deleted").value(1));

        verify(jds).delete(jd);
    }

    @Test
    void a_changed_posting_is_written_in_place() throws Exception {
        stubAnEmptyWorkspace();
        UUID jdId = UUID.fromString("55555555-5555-5555-5555-555555555555");
        JobJd existing = new JobJd();
        when(jds.findByIdAndUserId(eq(jdId), eq(UUID.fromString(USER))))
                .thenReturn(Optional.of(existing));
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("job_descriptions", List.of(
                        Map.of("op", "update", "id", jdId.toString())))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.2.0","data":{
                                  "job_descriptions":[{"id":"55555555-5555-5555-5555-555555555555",
                                    "raw_text":"We are hiring backend engineers.",
                                    "parsed":{"title":"Backend Engineer"}}]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.job_descriptions.updated").value(1))
                .andExpect(jsonPath("$.data.applied.job_descriptions.created").value(0));

        ArgumentCaptor<JobJd> written = ArgumentCaptor.forClass(JobJd.class);
        verify(jds).save(written.capture());
        assertThat(written.getValue()).isSameAs(existing);
        assertThat(written.getValue().getRawText()).isEqualTo("We are hiring backend engineers.");
        assertThat(written.getValue().getParsed()).containsEntry("title", "Backend Engineer");
    }

    @Test
    void a_retired_interview_is_deleted_whole() throws Exception {
        stubAnEmptyWorkspace();
        UUID sessionId = UUID.fromString("66666666-6666-6666-6666-666666666666");
        InterviewSession session = new InterviewSession();
        when(sessions.findByIdAndUserId(eq(sessionId), eq(UUID.fromString(USER))))
                .thenReturn(Optional.of(session));
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("interviews", List.of(
                        Map.of("op", "delete", "id", sessionId.toString())))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.2.0","data":{"interviews":[]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.interviews.deleted").value(1));

        // The turns and the report cascade with the session; the delete is the
        // one the interview's own screen uses.
        verify(sessions).delete(session);
    }

    @Test
    void an_unchanged_interview_is_not_written_again() throws Exception {
        stubAnEmptyWorkspace();
        UUID sessionId = UUID.fromString("77777777-7777-7777-7777-777777777777");
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("interviews", List.of(
                        Map.of("op", "skip", "id", sessionId.toString())))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.2.0","data":{
                                  "interviews":[{"id":"77777777-7777-7777-7777-777777777777",
                                    "mode":"mixed"}]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.interviews.unchanged").value(1))
                .andExpect(jsonPath("$.data.applied.interviews.created").value(0));

        verify(sessions, never()).save(any());
        verify(turns, never()).save(any());
        verify(evaluations, never()).save(any());
    }

    /**
     * The transcript is replaced on an update, and the report with it.
     *
     * <p>The bundle carries the transcript whole, so the restore is the
     * document a second time: a turn the bundle no longer names is a turn the
     * restore was asked to take back. Merging would keep an answer the file
     * does not carry -- and the report is about the answers, so it is
     * replaced too.
     */
    @Test
    void a_changed_interview_replaces_its_transcript() throws Exception {
        stubAnEmptyWorkspace();
        UUID sessionId = UUID.fromString("88888888-8888-8888-8888-888888888888");
        InterviewSession session = new InterviewSession();
        InterviewTurn staleTurn = new InterviewTurn();
        InterviewEvaluation staleReport = new InterviewEvaluation();
        when(sessions.findByIdAndUserId(eq(sessionId), eq(UUID.fromString(USER))))
                .thenReturn(Optional.of(session));
        when(turns.findBySessionIdOrderBySeqAsc(any())).thenReturn(List.of(staleTurn));
        when(evaluations.findBySessionId(any())).thenReturn(Optional.of(staleReport));
        when(sessions.save(any())).thenAnswer(call -> call.getArgument(0));
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("interviews", List.of(
                        Map.of("op", "update", "id", sessionId.toString())))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.2.0","data":{
                                  "interviews":[{"id":"88888888-8888-8888-8888-888888888888",
                                    "mode":"technical","status":"completed",
                                    "turns":[{"seq":1,"role":"interviewer",
                                              "content":"Why us?"}],
                                    "evaluation":{"dims":{"communication":4},
                                                  "summary":{"well":["clear"]},
                                                  "trajectory":[]}}]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.interviews.updated").value(1))
                .andExpect(jsonPath("$.data.applied.interviews.created").value(0));

        verify(turns).deleteAll(List.of(staleTurn));
        verify(evaluations).delete(staleReport);
        ArgumentCaptor<InterviewTurn> turn = ArgumentCaptor.forClass(InterviewTurn.class);
        verify(turns).save(turn.capture());
        assertThat(turn.getValue().getContent()).isEqualTo("Why us?");
        verify(evaluations).save(any());
    }

    /**
     * A chat is restored with the transcript the bundle carries, whole.
     *
     * <p>The chat is the one row the candidate did not type: it is what they
     * asked and what the assistant answered, and a restore that kept the title
     * and dropped the messages would restore an empty room. The transcript is
     * replaced rather than merged for the same reason the interview's is -- a
     * chat holding half of each conversation is not either one.
     */
    @Test
    void a_changed_chat_replaces_its_transcript() throws Exception {
        stubAnEmptyWorkspace();
        UUID chatId = UUID.fromString("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
        Conversation chat = new Conversation();
        identify(chat, chatId);
        chat.setUserId(UUID.fromString(USER));
        Message stale = new Message();
        stale.setConversationId(chatId);
        when(conversations.findByIdAndUserId(eq(chatId), eq(UUID.fromString(USER))))
                .thenReturn(Optional.of(chat));
        when(messages.findByConversationIdOrderByCreatedAtAsc(chatId))
                .thenReturn(List.of(stale));
        when(conversations.save(any())).thenAnswer(call -> call.getArgument(0));
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("conversations", List.of(
                        Map.of("op", "update", "id", chatId.toString())))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.3.0","data":{
                                  "conversations":[{"id":"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                                    "title":"Why is my match low?",
                                    "context":{"resumeId":"r1"},
                                    "messages":[{"role":"assistant",
                                      "content":"The posting asks for Go.",
                                      "sources":[{"kind":"job","id":"j1"}],
                                      "actions":[]}]}]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.conversations.updated").value(1))
                .andExpect(jsonPath("$.data.applied.conversations.created").value(0));

        verify(messages).deleteAll(List.of(stale));
        ArgumentCaptor<Message> written = ArgumentCaptor.forClass(Message.class);
        verify(messages).save(written.capture());
        assertThat(written.getValue().getConversationId()).isEqualTo(chatId);
        assertThat(written.getValue().getUserId()).isEqualTo(UUID.fromString(USER));
        assertThat(written.getValue().getContent()).isEqualTo("The posting asks for Go.");
        assertThat(written.getValue().getSources()).hasSize(1);
        assertThat(chat.getTitle()).isEqualTo("Why is my match low?");
        assertThat(chat.getContext()).containsEntry("resumeId", "r1");
    }

    /**
     * A chat the bundle no longer carries is retired, and its messages with it.
     */
    @Test
    void a_retired_chat_is_deleted_whole() throws Exception {
        stubAnEmptyWorkspace();
        UUID chatId = UUID.fromString("cccccccc-cccc-cccc-cccc-cccccccccccc");
        Conversation chat = new Conversation();
        identify(chat, chatId);
        chat.setUserId(UUID.fromString(USER));
        when(conversations.findByIdAndUserId(eq(chatId), eq(UUID.fromString(USER))))
                .thenReturn(Optional.of(chat));
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("sections", Map.of("conversations", List.of(
                        Map.of("op", "delete", "id", chatId.toString())))));

        mvc.perform(post("/api/v1/data-portability/import-apply")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"bundle":{"schema_version":"1.3.0","data":{"conversations":[]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.applied.conversations.deleted").value(1));

        verify(conversations).delete(chat);
    }

    /**
     * The preview reads the workspace when the caller sends no state.
     *
     * <p>The plan is a comparison, so a preview with no other half calls every
     * row a create -- counts about a workspace nobody has, which the apply
     * then contradicts. The browser's preview sends no state (the engine reads
     * its own six sections), so the backend has to read the four it owns.
     */
    @Test
    void the_preview_reads_the_workspace_when_the_caller_sends_no_state() throws Exception {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(
                eq(UUID.fromString(USER)), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(growthPlans.findByUserIdOrderByCreatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(notes.findByUserId(eq(UUID.fromString(USER)))).thenReturn(List.of());
        when(contacts.findByUserIdOrderByUpdatedAtDesc(eq(UUID.fromString(USER))))
                .thenReturn(List.of());
        when(profiles.findByUserId(eq(UUID.fromString(USER)))).thenReturn(Optional.empty());
        when(ai.importPlan(eq(UUID.fromString(USER)), any(), any()))
                .thenReturn(Map.of("op_counts", Map.of()));

        mvc.perform(post("/api/v1/data-portability/import-plan")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"bundle\":{\"schema_version\":\"1.2.0\"}}"))
                .andExpect(status().isOk());

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> existing = ArgumentCaptor.forClass(Map.class);
        verify(ai).importPlan(eq(UUID.fromString(USER)), any(), existing.capture());
        @SuppressWarnings("unchecked")
        Map<String, Object> state = (Map<String, Object>) existing.getValue().get("data");
        assertThat(state).containsKeys(
                "applications", "growth_plans", "notes", "contacts", "conversations", "profile");
    }
}
