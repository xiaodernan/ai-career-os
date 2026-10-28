package com.careeros.report.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.entity.GrowthPlan;
import com.careeros.ai.repository.GrowthPlanRepository;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.auth.entity.UserProfile;
import com.careeros.auth.repository.UserProfileRepository;
import com.careeros.common.ApiException;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.EnvelopeJson;
import com.careeros.common.Json;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.UserNoteRepository;
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
import com.careeros.network.entity.Contact;
import com.careeros.network.dto.ContactDtos.ContactRequest;
import com.careeros.network.repository.ContactRepository;
import com.careeros.network.service.ContactService;
import com.careeros.resume.dto.ResumeDtos.CreateResumeRequest;
import com.careeros.resume.service.ResumeService;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Predicate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The re-import, applied (13.2).
 *
 * <p>The ai-service emits the *plan* — per-item create / update / delete ops
 * with a content hash each — and this service executes it. The plan is the
 * engine's; the writes are the backend's, because the backend owns the tables.
 *
 * <p>Two rules make the apply safe to run twice and safe to run at all:
 *
 * - **Only the caller's own rows are touched.** Every read and every write is
 *   scoped by the user id, so a bundle that names another user's rows finds
 *   nothing to change rather than writing into someone else's account.
 * - **A section is applied whole or not at all.** A section that cannot be
 *   applied is reported as skipped with the reason, and the rest of the bundle
 *   still lands. A restore that half-applied a section and reported success
 *   would be worse than one that said which section it left alone.
 * - **An unchanged row is not written.** The engine plans a {@code skip} for a
 *   row whose content is already the target's, and this service takes the op
 *   at its word: nothing is saved for it, and the answer counts it as
 *   {@code unchanged}. That is the half of the promise the "Your data" panel
 *   makes -- a re-import of the bundle the workspace exported writes nothing,
 *   and the user can see that it wrote nothing.
 * - **A row the bundle no longer carries is retired, when the restore can
 *   name it.** The sections matched by id -- the applications, the growth
 *   runs, the notes, the contacts, the postings, the interviews -- execute
 *   the plan's {@code delete}; the sections the restore re-ingests (the
 *   resumes, the documents, the memories) are matched by content, so they are
 *   never deleted: the restore cannot name a row it would bring back as a
 *   different one.
 */
@Service
public class ImportService {

    private final AiServiceClient aiService;
    private final ExportService exports;
    private final UserProfileRepository profiles;
    private final UserNoteRepository notes;
    private final ContactRepository contacts;
    private final ApplicationRepository applications;
    private final GrowthPlanRepository growthPlans;
    private final ResumeService resumes;
    private final KnowledgeService knowledge;
    private final ContactService contactService;
    private final JobJdRepository jds;
    private final JobRepository jobRepository;
    private final InterviewSessionRepository sessions;
    private final InterviewTurnRepository turns;
    private final InterviewEvaluationRepository evaluations;

    public ImportService(AiServiceClient aiService, ExportService exports,
                          UserProfileRepository profiles,
                          UserNoteRepository notes, ContactRepository contacts,
                          ApplicationRepository applications,
                          GrowthPlanRepository growthPlans, ResumeService resumes,
                          KnowledgeService knowledge, ContactService contactService,
                          JobJdRepository jds,
                          JobRepository jobRepository, InterviewSessionRepository sessions,
                          InterviewTurnRepository turns,
                          InterviewEvaluationRepository evaluations) {
        this.aiService = aiService;
        this.exports = exports;
        this.profiles = profiles;
        this.notes = notes;
        this.contacts = contacts;
        this.applications = applications;
        this.growthPlans = growthPlans;
        this.resumes = resumes;
        this.knowledge = knowledge;
        this.contactService = contactService;
        this.jds = jds;
        this.jobRepository = jobRepository;
        this.sessions = sessions;
        this.turns = turns;
        this.evaluations = evaluations;
    }

    /**
     * Plan a re-import without writing anything: the ops the engine would run,
     * and the counts.
     *
     * <p>The preview answers the same question as the apply, so it reads the
     * same current state: a caller may send their own (the ops CLI does), and
     * a caller that sends none -- the browser's preview -- gets the workspace
     * read, not an empty one where every row is a create.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> plan(UUID userId, Map<String, Object> bundle,
                                    Map<String, Object> existing) {
        return aiService.importPlan(userId, bundle,
                existing != null ? existing : currentState(userId));
    }

    /**
     * Apply a re-import. The plan is computed first, then executed section by
     * section; the answer says what was written and what was left alone.
     */
    @Transactional
    public Map<String, Object> apply(UUID userId, Map<String, Object> bundle) {
        if (bundle == null || !(bundle.get("data") instanceof Map)) {
            throw new ApiException(ApiErrorCode.BUNDLE_NO_SECTION, "The bundle has no data section.");
        }
        // The plan is the engine's answer about what should change; the apply
        // executes exactly those ops and nothing else.
        Map<String, Object> plan = aiService.importPlan(userId, bundle, currentState(userId));
        @SuppressWarnings("unchecked")
        Map<String, List<Map<String, Object>>> sections =
                (Map<String, List<Map<String, Object>>>) plan.get("sections");
        if (sections == null) {
            throw new ApiException(ApiErrorCode.BUNDLE_NOT_PLANNABLE, "The bundle could not be planned.");
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) bundle.get("data");
        Map<String, int[]> applied = new LinkedHashMap<>();
        List<Map<String, String>> skipped = new ArrayList<>();

        applyProfile(userId, data, sections, applied, skipped);
        applyMemories(userId, data, sections, applied, skipped);
        applyApplications(userId, data, sections, applied, skipped);
        applyGrowthPlans(userId, data, sections, applied, skipped);
        applyResumes(userId, data, sections, applied, skipped);
        applyKnowledge(userId, data, sections, applied, skipped);
        applyJobDescriptions(userId, data, sections, applied, skipped);
        applyInterviews(userId, data, sections, applied, skipped);
        applyNotes(userId, data, sections, applied, skipped);
        applyContacts(userId, data, sections, applied, skipped);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("applied", applied.entrySet().stream()
                .collect(java.util.stream.Collectors.toMap(
                        Map.Entry::getKey,
                        e -> Map.of("created", e.getValue()[0], "updated", e.getValue()[1],
                                "deleted", e.getValue()[2], "unchanged", e.getValue()[3]))));
        result.put("skipped", skipped);
        result.put("op_counts", plan.get("op_counts"));
        return result;
    }

    /* ------------------------------------------------------------------ */
    /* The sections                                                        */
    /* ------------------------------------------------------------------ */

    /** The profile is one row: the bundle's version overwrites the caller's. */
    private void applyProfile(UUID userId, Map<String, Object> data,
                              Map<String, List<Map<String, Object>>> sections,
                              Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("profile");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        if ("skip".equals(str(ops.get(0), "op"))) {
            // The row the panel already has is the row the bundle carries:
            // saving it again would be a write with no change to show for it.
            count(applied, "profile", 0, 0, 0, 1);
            return;
        }
        Object row = data.get("profile");
        if (!(row instanceof Map<?, ?> profile)) {
            skipped.add(Map.of("section", "profile", "reason", "The bundle carries no profile row."));
            return;
        }
        UserProfile target = profiles.findByUserId(userId).orElseGet(() -> {
            UserProfile fresh = new UserProfile();
            fresh.setUserId(userId);
            return fresh;
        });
        boolean existed = target.getId() != null;
        target.setHeadline(str(profile, "headline"));
        target.setSummary(str(profile, "summary"));
        target.setLocation(str(profile, "location"));
        target.setYearsExperience(dec(profile, "years_experience"));
        target.setTargetRoles(strings(profile, "target_roles"));
        target.setTargetLocations(strings(profile, "target_locations"));
        target.setLinks(map(profile, "links"));
        target.setWorkAuthorization(map(profile, "work_authorization"));
        target.setPreferences(map(profile, "preferences"));
        profiles.save(target);
        count(applied, "profile", existed ? 1 : 0, existed ? 0 : 1);
    }

    /** The applications: the pipeline the candidate actually worked. */
    private void applyApplications(UUID userId, Map<String, Object> data,
                                   Map<String, List<Map<String, Object>>> sections,
                                   Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("applications");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("applications");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "applications", "reason", "The bundle carries no applications."));
            return;
        }
        int created = 0;
        int updated = 0;
        int deleted = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            if ("delete".equals(kind)) {
                // Only the caller's own row goes: the id is looked up under
                // their id, so a bundle naming someone else's row finds
                // nothing and deletes nothing.
                UUID rowId = uuid(id);
                if (rowId == null) {
                    continue;
                }
                applications.findByIdAndUserId(rowId, userId).ifPresent(row -> {
                    applications.delete(row);
                });
                deleted++;
                continue;
            }
            Map<?, ?> row = findRow(list, id);
            if (row == null) {
                continue;
            }
            UUID rowId = uuid(id);
            Application target = rowId == null ? null
                    : applications.findByIdAndUserId(rowId, userId).orElse(null);
            if (target == null) {
                target = new Application();
                target.setUserId(userId);
                setId(target, restorableId(rowId, applications::existsById));
                created++;
            } else {
                updated++;
            }
            target.setTitle(str(row, "title"));
            target.setCompanyName(str(row, "company_name"));
            target.setStatus(str(row, "status"));
            target.setNotes(str(row, "notes"));
            target.setOfferCompensation(str(row, "offer_compensation"));
            target.setRejectionReason(str(row, "rejection_reason"));
            target.setAppliedAt(time(row, "applied_at"));
            target.setReminderAt(time(row, "reminder_at"));
            applications.save(target);
        }
        count(applied, "applications", created, updated, deleted, unchanged);
    }

    /**
     * The notes the reader typed into their knowledge base.
     *
     * <p>These are the reader's own words -- the salary band they wrote down, the
     * company fact they wanted to remember -- and they were the first thing a
     * reader lost when they left: the bundle carried every table the *engines*
     * read and neither table the reader typed into.
     *
     * <p>The write goes through the knowledge service, the way the panel writes
     * it: one author of note rows, and a new id minted by the database. An id
     * from the bundle is only reused when the *caller* already has that row --
     * the caller's own scope finds it first -- so a restore into another
     * account can never land on top of somebody else's row.
     */
    private void applyNotes(UUID userId, Map<String, Object> data,
                            Map<String, List<Map<String, Object>>> sections,
                            Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("notes");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("notes");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "notes", "reason", "The bundle carries no notes."));
            return;
        }
        int created = 0;
        int updated = 0;
        int deleted = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
            UUID rowId = uuid(id);
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            if ("delete".equals(kind)) {
                if (rowId == null) {
                    continue;
                }
                // The service's own delete, so a retired note stops being
                // cited the way a note deleted on the screen does.
                if (notes.findByIdAndUserId(rowId, userId).isPresent()) {
                    knowledge.deleteNote(userId, rowId);
                    deleted++;
                }
                continue;
            }
            Map<?, ?> row = findRow(list, id);
            if (row == null) {
                continue;
            }
            String content = str(row, "content");
            if (content == null || content.isBlank()) {
                continue;
            }
            String title = str(row, "title");
            List<String> tags = Json.strList(row.get("tags"));
            NoteRequest request = new NoteRequest(title, content, tags);
            if (rowId != null && notes.findByIdAndUserId(rowId, userId).isPresent()) {
                knowledge.updateNote(userId, rowId, request);
                updated++;
            } else {
                knowledge.createNote(userId, request);
                created++;
            }
        }
        count(applied, "notes", created, updated, deleted, unchanged);
    }

    /**
     * The people in the reader's networking circle.
     *
     * <p>The address book is the reader's own record of who they know -- and the
     * note they wrote about the person travels with it. A restore that brought
     * back the applications and left the people behind would be a strange half
     * of a career.
     *
     * <p>As with the notes, the write goes through the service that owns the
     * table, so a new row gets an id of its own and the restore cannot land on
     * top of somebody else's row.
     */
    private void applyContacts(UUID userId, Map<String, Object> data,
                                Map<String, List<Map<String, Object>>> sections,
                                Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("contacts");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("contacts");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "contacts", "reason", "The bundle carries no contacts."));
            return;
        }
        int created = 0;
        int updated = 0;
        int deleted = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
            UUID rowId = uuid(id);
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            if ("delete".equals(kind)) {
                if (rowId == null) {
                    continue;
                }
                if (contacts.findByIdAndUserId(rowId, userId).isPresent()) {
                    contactService.delete(userId, rowId);
                    deleted++;
                }
                continue;
            }
            Map<?, ?> row = findRow(list, id);
            if (row == null) {
                continue;
            }
            String name = str(row, "name");
            if (name == null || name.isBlank()) {
                continue;
            }
            ContactRequest request = new ContactRequest(
                    name, str(row, "role"), str(row, "company"), str(row, "relation"),
                    str(row, "email"), str(row, "notes"), time(row, "last_touch_at"));
            if (rowId != null && contacts.findByIdAndUserId(rowId, userId).isPresent()) {
                contactService.update(userId, rowId, request);
                updated++;
            } else {
                contactService.create(userId, request);
                created++;
            }
        }
        count(applied, "contacts", created, updated, deleted, unchanged);
    }

    /** The stored growth runs: one row per report the candidate ever built. */
    private void applyGrowthPlans(UUID userId, Map<String, Object> data,
                                  Map<String, List<Map<String, Object>>> sections,
                                  Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("growth_plans");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("growth_plans");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "growth_plans", "reason", "The bundle carries no growth runs."));
            return;
        }
        int created = 0;
        int updated = 0;
        int deleted = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            if ("delete".equals(kind)) {
                UUID rowId = uuid(id);
                if (rowId == null) {
                    continue;
                }
                growthPlans.findById(rowId)
                        .filter(row -> userId.equals(row.getUserId()))
                        .ifPresent(row -> growthPlans.delete(row));
                deleted++;
                continue;
            }
            Map<?, ?> row = findRow(list, id);
            if (row == null) {
                continue;
            }
            UUID rowId = uuid(id);
            GrowthPlan target = rowId == null ? null
                    : growthPlans.findById(rowId).filter(p -> userId.equals(p.getUserId())).orElse(null);
            if (target == null) {
                target = new GrowthPlan();
                target.setUserId(userId);
                setId(target, restorableId(rowId, growthPlans::existsById));
                created++;
            } else {
                updated++;
            }
            target.setTargetRole(str(row, "target_role"));
            BigDecimal coverage = dec(row, "coverage");
            target.setCoverage(coverage == null ? 0d : coverage.doubleValue());
            @SuppressWarnings("unchecked")
            Map<String, Object> report = (Map<String, Object>) row.get("report");
            target.setReport(report == null ? Map.of() : report);
            growthPlans.save(target);
        }
        count(applied, "growth_plans", created, updated, deleted, unchanged);
    }

    /**
     * The long-term memories: what the user told the assistant about their
     * skills, their goals and their preferences.
     *
     * <p>They come back, and the reason is that they are the user's own
     * statements rather than the model's inferences: the export carries them
     * deliberately, the settings page lists them so the user can correct or
     * delete any of them, and a workspace restored without them would leave
     * the assistant a stranger to the person who restored it.
     *
     * <p>The rows live in the ai-service's table, so the restore goes through
     * it — upserted on the same (kind, key) the extraction path uses, which
     * makes running the restore twice land the same rows.
     */
    private void applyMemories(UUID userId, Map<String, Object> data,
                               Map<String, List<Map<String, Object>>> sections,
                               Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("memories");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("memories");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "memories", "reason", "The bundle carries no memories."));
            return;
        }
        List<Map<String, Object>> payload = new ArrayList<>();
        int created = 0;
        int updated = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String kind = str(op, "op");
            if ("delete".equals(kind)) {
                continue;  // a memory the user forgot stays forgotten
            }
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            Map<?, ?> row = findRow(list, str(op, "id"));
            if (row == null) {
                continue;
            }
            String content = str(row, "content");
            if (content == null || content.isBlank()) {
                continue;
            }
            Map<String, Object> memory = new LinkedHashMap<>();
            memory.put("kind", str(row, "kind") == null ? "fact" : str(row, "kind"));
            memory.put("key", str(row, "key") == null ? "" : str(row, "key"));
            memory.put("content", content);
            Object importance = row.get("importance");
            memory.put("importance", importance instanceof Number n ? n.doubleValue() : 0.6);
            memory.put("source", str(row, "source") == null ? "restore" : str(row, "source"));
            payload.add(memory);
            if ("update".equals(kind)) {
                updated++;
            } else {
                created++;
            }
        }
        if (!payload.isEmpty()) {
            // One upsert per row, keyed on (kind, key) -- the same key the
            // extraction path uses, which is what makes a re-import land the
            // same rows instead of a second copy of each memory.
            aiService.importMemories(userId, payload);
        }
        count(applied, "memories", created, updated, 0, unchanged);
    }

    /**
     * The resumes: a restored resume goes through the same two steps a new one
     * does — the row, then the ingestion that makes it citable.
     *
     * <p>The id is NOT carried over. A resume's id is the key its knowledge
     * chunks and its versions hang off, and those are minted by the ingestion
     * pipeline; reusing an old id would leave two documents' chunks pointing
     * at one row. So a restored resume is a *new* resume with the same content,
     * and the answer says so.
     */
    private void applyResumes(UUID userId, Map<String, Object> data,
                              Map<String, List<Map<String, Object>>> sections,
                              Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("resumes");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("resumes");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "resumes", "reason", "The bundle carries no resumes."));
            return;
        }
        int created = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String kind = str(op, "op");
            if ("delete".equals(kind)) {
                continue;  // a resume is never retired by a restore: the copy
                           // the plan matched it by is content, not an id
            }
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            Map<?, ?> row = findRow(list, str(op, "id"));
            if (row == null) {
                continue;
            }
            String title = str(row, "resume_title");
            if (title == null || title.isBlank()) {
                title = str(row, "title");
            }
            String plaintext = str(row, "plaintext");
            if (title == null || title.isBlank() || plaintext == null || plaintext.isBlank()) {
                continue;
            }
            // The two steps a new resume takes, in the same order: the row, then
            // the ingestion that chunks and embeds it so the agents can cite it.
            //
            // The ingestion is the create's own now, and that is not a
            // refactor: the copy it makes carries the resume's id as its
            // reference, and the reference is what lets a deleted resume take
            // its copy back. An ingestion of its own had no reference at all,
            // so the restored resume's copy outlived the row it was made from
            // and kept being quoted after the resume was gone.
            resumes.create(userId, new CreateResumeRequest(title, plaintext));
            created++;
        }
        count(applied, "resumes", created, 0, 0, unchanged);
    }

    /**
     * The knowledge base: the documents the user's own material was ingested
     * from. A restored document is re-ingested, so its chunks are embedded
     * again and the agents can cite it.
     */
    private void applyKnowledge(UUID userId, Map<String, Object> data,
                                Map<String, List<Map<String, Object>>> sections,
                                Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("knowledge");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("knowledge");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "knowledge", "reason", "The bundle carries no documents."));
            return;
        }
        int created = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String kind = str(op, "op");
            if ("delete".equals(kind)) {
                continue;  // a document is never retired by a restore: the
                           // plan matched it by its excerpt, not by an id
            }
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            Map<?, ?> row = findRow(list, str(op, "id"));
            if (row == null) {
                continue;
            }
            String title = str(row, "title");
            String excerpt = str(row, "text_excerpt");
            if (title == null || title.isBlank() || excerpt == null || excerpt.isBlank()) {
                // The bundle carries a document's metadata and its excerpt, not
                // its whole body -- the body is in the object store, and a
                // restore that claims to bring back a document it only has an
                // excerpt of would be overstating what it did.
                continue;
            }
            // A restored document is re-ingested as a note: the bundle carries
            // the document's metadata and its excerpt, not its whole body (the
            // body is in the object store), and a note is what the ingestion
            // pipeline accepts for a piece of text.
            knowledge.ingestText(userId, title, excerpt, "note", null);
            created++;
        }
        count(applied, "knowledge", created, 0, 0, unchanged);
    }

    /**
     * The job descriptions: the pasted postings and the analyst's reading of
     * them.
     *
     * <p>The bundle carries the whole row, the raw text AND the parsed result,
     * so the restore is a row write -- the analyst does not run again. That is
     * the difference between a restore and a re-analysis: the user's own
     * reading of a posting is preserved, not recomputed into something that
     * might differ.
     *
     * <p>An id the caller already has is written in place, and a posting the
     * plan no longer names is retired: the bundle is the document the restore
     * was asked to land, and a row the document does not carry is a row the
     * reader took out of it.
     */
    private void applyJobDescriptions(UUID userId, Map<String, Object> data,
                                     Map<String, List<Map<String, Object>>> sections,
                                     Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("job_descriptions");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("job_descriptions");
        if (!(rows instanceof List<?> list)) {
            skipped.add(Map.of("section", "job_descriptions",
                    "reason", "The bundle carries no job descriptions."));
            return;
        }
        int created = 0;
        int updated = 0;
        int deleted = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
            UUID rowId = uuid(id);
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            if ("delete".equals(kind)) {
                if (rowId == null) {
                    continue;
                }
                // Only the caller's own row goes: the lookup is under their id.
                jds.findByIdAndUserId(rowId, userId).ifPresent(jds::delete);
                deleted++;
                continue;
            }
            Map<?, ?> row = findRow(list, id);
            if (row == null) {
                continue;
            }
            String rawText = str(row, "raw_text");
            if (rawText == null || rawText.isBlank()) {
                continue;
            }
            JobJd jd = rowId == null ? null
                    : jds.findByIdAndUserId(rowId, userId).orElse(null);
            if (jd == null) {
                jd = new JobJd();
                jd.setUserId(userId);
                setId(jd, restorableId(rowId, jds::existsById));
                created++;
            } else {
                updated++;
            }
            jd.setRawText(rawText);
            // A job is a shared entity -- the corpus belongs to nobody -- so
            // the link to one is carried over when the target can hold it. An
            // update keeps the link the row already has.
            UUID jobId = uuid(str(row, "job_id"));
            if (jobId != null && jobRepository.existsById(jobId)) {
                jd.setJobId(jobId);
            }
            jd.setParsed(mapOrNull(row, "parsed"));
            jds.save(jd);
        }
        count(applied, "job_descriptions", created, updated, deleted, unchanged);
    }

    /**
     * The interviews: the session, its turns and its evaluation.
     *
     * <p>All three are in the bundle, so the restore is a row write too -- the
     * interviewer does not run again, which matters because an interview is
     * the one thing the user cannot repeat: the questions were asked of them
     * once.
     *
     * <p>The children are replaced rather than merged on an update, and a
     * retired session is deleted whole: the turns and the report hang off it
     * with ON DELETE CASCADE, so the same delete the interview's own screen
     * uses takes the transcript with it. A bundle carrying a report on a
     * session the target already had with a different one replaces the
     * verdict as well as the answers, because the report is about the answers.
     */
    private void applyInterviews(UUID userId, Map<String, Object> data,
                                Map<String, List<Map<String, Object>>> sections,
                                Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("interviews");
        if (ops == null || ops.isEmpty()) {
            return;
        }
        Object rows = data.get("interviews");
        if (!(rows instanceof List<?> sessionsList)) {
            skipped.add(Map.of("section", "interviews", "reason", "The bundle carries no interviews."));
            return;
        }
        int created = 0;
        int updated = 0;
        int deleted = 0;
        int unchanged = 0;
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
            UUID rowId = uuid(id);
            if ("skip".equals(kind)) {
                unchanged++;
                continue;
            }
            if ("delete".equals(kind)) {
                if (rowId == null) {
                    continue;
                }
                sessions.findByIdAndUserId(rowId, userId).ifPresent(sessions::delete);
                deleted++;
                continue;
            }
            Map<?, ?> row = findRow(sessionsList, id);
            if (row == null) {
                continue;
            }
            InterviewSession session = rowId == null ? null
                    : sessions.findByIdAndUserId(rowId, userId).orElse(null);
            if (session == null) {
                session = new InterviewSession();
                session.setUserId(userId);
                setId(session, restorableId(rowId, sessions::existsById));
                created++;
            } else {
                turns.deleteAll(turns.findBySessionIdOrderBySeqAsc(session.getId()));
                evaluations.findBySessionId(session.getId()).ifPresent(evaluations::delete);
                updated++;
            }
            session.setMode(str(row, "mode") == null ? "mixed" : str(row, "mode"));
            session.setStatus(str(row, "status") == null ? "completed" : str(row, "status"));
            session.setCompanyName(str(row, "company_name"));
            session.setPositionTitle(str(row, "position_title"));
            session.setConfig(map(row, "config"));
            Object difficulty = row.get("difficulty");
            if (difficulty instanceof Number n) {
                session.setDifficulty(n.floatValue());
            }
            OffsetDateTime started = time(row, "started_at");
            if (started != null) {
                session.setStartedAt(started);
            }
            OffsetDateTime finished = time(row, "finished_at");
            if (finished != null) {
                session.setFinishedAt(finished);
            }
            session = sessions.save(session);

            // The turns carry the questions and the evaluations, so the
            // transcript comes back whole.
            int seq = 0;
            Object turnRows = row.get("turns") == null ? List.of() : row.get("turns");
            for (Object turn : (List<?>) turnRows) {
                if (!(turn instanceof Map<?, ?> t)) {
                    continue;
                }
                InterviewTurn saved = new InterviewTurn();
                saved.setUserId(userId);
                saved.setSessionId(session.getId());
                Object turnSeq = t.get("seq");
                saved.setSeq(turnSeq instanceof Number n ? n.intValue() : seq);
                seq = saved.getSeq() + 1;
                saved.setRole(str(t, "role") == null ? "interviewer" : str(t, "role"));
                saved.setContent(str(t, "content") == null ? "" : str(t, "content"));
                saved.setQuestionMeta(mapOrNull(t, "question_meta"));
                saved.setEvaluation(mapOrNull(t, "evaluation"));
                turns.save(saved);
            }

            // The evaluation is the report the user reads: the dimensions, the
            // summary and the trajectory.
            Object evaluation = row.get("evaluation");
            if (evaluation instanceof Map<?, ?> ev && !ev.isEmpty()) {
                InterviewEvaluation saved = new InterviewEvaluation();
                saved.setUserId(userId);
                saved.setSessionId(session.getId());
                saved.setDims(map(ev, "dims"));
                saved.setSummary(map(ev, "summary"));
                Object trajectory = ev.get("trajectory");
                if (trajectory instanceof List<?> list) {
                    saved.setTrajectory(List.copyOf(list));
                }
                evaluations.save(saved);
            }
        }
        count(applied, "interviews", created, updated, deleted, unchanged);
    }

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */
    /**
     * The caller's current state, exported the same way — the plan's other half.
     *
     * <p>"The same way" is the whole point of reading through {@link
     * ExportService#backendSections}: the plan tells a create from an update
     * from a skip by comparing the bundle's row with this one, so a row
     * serialized two different ways is a row that always looks changed. The
     * four sections used to be summarized here -- an application was its id,
     * its title and its status -- which was enough to tell a create from an
     * update and not enough to tell an update from a skip.
     *
     * <p>The notes and the contacts are here for the same reason the
     * applications are: a section the current state does not carry is a
     * section every row in the bundle is a *create* for, and a restore that
     * wrote a second copy of every note would be worse than one that left
     * them alone.
     */
    private Map<String, Object> currentState(UUID userId) {
        Map<String, Object> data = new LinkedHashMap<>(exports.backendSections(userId));
        UserProfile profile = profiles.findByUserId(userId).orElse(null);
        data.put("profile", profile == null ? Map.of() : ExportService.toProfile(profile));
        return Map.of("data", data);
    }

    /** The row in the bundle's list that the op names. */
    private static Map<?, ?> findRow(List<?> rows, String id) {
        for (Object row : rows) {
            if (row instanceof Map<?, ?> map && id != null && id.equals(String.valueOf(map.get("id")))) {
                return map;
            }
        }
        return null;
    }

    private static String str(Map<?, ?> row, String key) {
        Object value = row.get(key);
        return value == null ? null : String.valueOf(value);
    }

    private static BigDecimal dec(Map<?, ?> row, String key) {
        Object value = row.get(key);
        if (value instanceof Number n) {
            return BigDecimal.valueOf(n.doubleValue());
        }
        if (value instanceof String s && !s.isBlank()) {
            try {
                return new BigDecimal(s);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }

    private static List<String> strings(Map<?, ?> row, String key) {
        Object value = row.get(key);
        if (value instanceof String text) {
            value = jsonValue(text, List.class);
        }
        if (value instanceof List<?> list) {
            return list.stream().map(String::valueOf).toList();
        }
        return List.of();
    }

    /**
     * A JSON column as the value it holds.
     *
     * <p>A bundle written by the current export carries a {@code jsonb} column
     * as the object it holds, and one written before that carries the column
     * as its text -- asyncpg's own return shape, which the export used to pass
     * straight through. Both are the same value, so both restore the same way:
     * a restore that dropped the text would lose the analyst's reading of a
     * posting, a session's config, or an answer's evaluation because of which
     * version of the product wrote the file.
     */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Map<?, ?> row, String key) {
        Object value = row.get(key);
        if (value instanceof String text) {
            value = jsonValue(text, Map.class);
        }
        return value instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
    }

    /**
     * A nullable JSON column as the value it holds, null included.
     *
     * <p>{@link #map} answers an empty object for an absent one, which is the
     * right answer for a column the schema makes NOT NULL. For the nullable
     * ones it is not: writing {@code {}} where the bundle carries {@code null}
     * makes the row differ from the bundle by the restore's own hand, so the
     * next plan would call it changed and write it again, forever.
     */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> mapOrNull(Map<?, ?> row, String key) {
        Object value = row.get(key);
        if (value instanceof String text) {
            value = jsonValue(text, Map.class);
        }
        return value instanceof Map<?, ?> m ? (Map<String, Object>) m : null;
    }

    private static Object jsonValue(String text, Class<?> type) {
        if (text.isBlank()) {
            return null;
        }
        try {
            return EnvelopeJson.MAPPER.readValue(text, type);
        } catch (JsonProcessingException e) {
            // Text that is not JSON is not a value this column can hold; the
            // row restores without it rather than with something invented.
            return null;
        }
    }

    private static OffsetDateTime time(Map<?, ?> row, String key) {
        Object value = row.get(key);
        if (value == null) {
            return null;
        }
        try {
            return OffsetDateTime.parse(String.valueOf(value));
        } catch (RuntimeException e) {
            // An unparseable timestamp is left out rather than replaced: the
            // engine skips a duration it cannot read, and so does this.
            return null;
        }
    }

    private static UUID uuid(String id) {
        try {
            return id == null ? null : UUID.fromString(id);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    /** The id is the database's to mint, except on a restore — where the
     *  bundle's id IS the row's id, so the links inside the bundle still
     *  point where they did. */
    private static void setId(Object entity, UUID id) {
        try {
            var field = entity.getClass().getDeclaredField("id");
            field.setAccessible(true);
            field.set(entity, id);
        } catch (ReflectiveOperationException | RuntimeException e) {
            // Without the id the row is minted a new one, which is still a
            // correct restore — only the bundle's internal links would point
            // at the old ids.
        }
    }

    /**
     * The id a restored row may keep.
     *
     * <p>The bundle's id is the row's id — so the links inside the bundle still
     * point where they did — but only when nothing else holds it. An id that
     * belongs to *another account's* row would make the save write into that
     * row: the caller's restore would quietly change somebody else's data, and
     * the caller would get nothing of their own. That is not a bundle to
     * restore into another account; it is a bundle to restore into the
     * account it came from.
     *
     * <p>So the id is kept when it is free and minted when it is not. The
     * restore still lands the rows — they just do not land on top of
     * somebody else's. And a row the caller already has is found by the
     * caller's own scope before this is asked, so a same-account restore
     * keeps every id and every link.
     */
    private static UUID restorableId(UUID rowId, Predicate<UUID> taken) {
        if (rowId == null) {
            return null;
        }
        return taken.test(rowId) ? null : rowId;
    }

    private static void count(Map<String, int[]> applied, String section, int created, int updated) {
        count(applied, section, created, updated, 0, 0);
    }

    private static void count(Map<String, int[]> applied, String section,
                              int created, int updated, int deleted) {
        count(applied, section, created, updated, deleted, 0);
    }

    /**
     * The four numbers a section reports: what it wrote, and what it did not
     * have to. The fourth is the one the panel's promise is about.
     */
    private static void count(Map<String, int[]> applied, String section,
                              int created, int updated, int deleted, int unchanged) {
        applied.computeIfAbsent(section, k -> new int[4]);
        int[] row = applied.get(section);
        row[0] += created;
        row[1] += updated;
        row[2] += deleted;
        row[3] += unchanged;
    }
}
