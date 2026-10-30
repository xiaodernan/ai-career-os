package com.careeros.report.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.entity.GrowthPlan;
import com.careeros.ai.repository.GrowthPlanRepository;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.Paging;
import com.careeros.conversation.entity.Conversation;
import com.careeros.conversation.entity.Message;
import com.careeros.conversation.repository.ConversationRepository;
import com.careeros.conversation.repository.MessageRepository;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.UserNoteRepository;
import com.careeros.job.entity.IngestionFeed;
import com.careeros.job.entity.SavedSearch;
import com.careeros.job.repository.IngestionFeedRepository;
import com.careeros.job.repository.SavedSearchRepository;
import com.careeros.network.entity.Contact;
import com.careeros.network.repository.ContactRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The export bundle (13.1), with the backend's own sections in it.
 *
 * <p>The ai-service reads six sections for itself and hashes the bundle; this
 * service reads the seven the BACKEND owns — {@code applications},
 * {@code growth_plans}, {@code notes}, {@code contacts},
 * {@code conversations}, {@code saved_searches} and {@code ingestion_feeds} —
 * and hands them over.
 * The hash is still computed in one place (the ai-service), so a bundle has one
 * hashing rule rather than one per producer, and a bundle without the pipeline the
 * candidate actually worked is a bundle of their reading list and nothing else.
 *
 * <p>The notes and the contacts are not a nicety: they are the reader's own words
 * and the people they know. "Your data" that leaves out the two tables the reader
 * typed into is not their data. The chats are the same argument one step further:
 * the reader's questions and the coaching they were given are the reader's own
 * words too, and a bundle without them loses the reasoning behind every resume
 * and plan the engines produced. The saved searches and the feeds are the
 * account's standing choices: the question the morning sweep speaks for and the
 * sources the ingester is pointed at -- leave them out, and a restored account
 * goes silent at the next sunrise.
 */
@Service
public class ExportService {

    /** The export walks the caller's whole history; a cap keeps the request bounded. */
    private static final int MAX_ROWS = 1000;

    private final AiServiceClient aiService;
    private final ApplicationRepository applications;
    private final GrowthPlanRepository growthPlans;
    private final UserNoteRepository notes;
    private final ContactRepository contacts;
    private final ConversationRepository conversations;
    private final MessageRepository messages;
    private final SavedSearchRepository savedSearches;
    private final IngestionFeedRepository feeds;

    public ExportService(AiServiceClient aiService, ApplicationRepository applications,
                          GrowthPlanRepository growthPlans, UserNoteRepository notes,
                          ContactRepository contacts, ConversationRepository conversations,
                          MessageRepository messages, SavedSearchRepository savedSearches,
                          IngestionFeedRepository feeds) {
        this.aiService = aiService;
        this.applications = applications;
        this.growthPlans = growthPlans;
        this.notes = notes;
        this.contacts = contacts;
        this.conversations = conversations;
        this.messages = messages;
        this.savedSearches = savedSearches;
        this.feeds = feeds;
    }

    /**
     * The export bundle for the caller: the ai-service's six sections plus the
     * backend's seven, hashed together.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> exportBundle(UUID userId, boolean anonymized) {
        return aiService.exportBundle(userId, anonymized, backendSections(userId));
    }

    /**
     * The sections the backend owns, in the bundle's own shape.
     *
     * <p>Package-private because the restore reads through it too: the plan's
     * {@code existing} half has to be the same serialization as the bundle's
     * rows, or a row would look changed merely because the two halves spelled
     * it differently -- and the "unchanged rows are skipped" promise would be
     * kept by an accident of matching spellings rather than by one serializer.
     */
    Map<String, Object> backendSections(UUID userId) {
        Map<String, Object> sections = new LinkedHashMap<>();
        sections.put("applications", applications
                .findByUserIdOrderByUpdatedAtDescIdAsc(userId, Paging.first(MAX_ROWS)).stream()
                .map(ExportService::toApplication)
                .toList());
        sections.put("growth_plans", growthPlans.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(ExportService::toGrowthPlan)
                .toList());
        sections.put("notes", notes.findByUserId(userId).stream()
                .map(ExportService::toNote)
                .toList());
        sections.put("contacts", contacts.findByUserIdOrderByUpdatedAtDesc(userId).stream()
                .map(ExportService::toContact)
                .toList());
        sections.put("conversations", conversationsOf(userId));
        sections.put("saved_searches", savedSearches
                .findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(ExportService::toSavedSearch)
                .toList());
        sections.put("ingestion_feeds", feeds
                .findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(ExportService::toIngestionFeed)
                .toList());
        return sections;
    }

    /**
     * The copilot chats, each with its transcript.
     *
     * <p>The reader's questions and the coaching they were given are the
     * reader's own words, and until 1.3.0 they were the largest table in the
     * product that "Export everything" left out. One query per page of chats
     * would walk the history a conversation at a time; the transcripts are
     * read in one statement and grouped here.
     */
    private List<Map<String, Object>> conversationsOf(UUID userId) {
        List<Conversation> rows = conversations
                .findByUserIdOrderByUpdatedAtDescIdAsc(userId, Paging.first(MAX_ROWS))
                .getContent();
        if (rows.isEmpty()) {
            return List.of();
        }
        List<UUID> ids = rows.stream().map(Conversation::getId).toList();
        Map<UUID, List<Map<String, Object>>> transcripts = new LinkedHashMap<>();
        for (Message message : messages.findByConversationIdInOrderByCreatedAtAscIdAsc(ids)) {
            transcripts.computeIfAbsent(message.getConversationId(), key -> new ArrayList<>())
                    .add(toMessage(message));
        }
        List<Map<String, Object>> out = new ArrayList<>(rows.size());
        for (Conversation c : rows) {
            out.add(toConversation(c, transcripts.getOrDefault(c.getId(), List.of())));
        }
        return out;
    }

    /**
     * One application as the bundle carries it. The field names are the row's
     * own columns, spelled in the bundle's snake_case convention — the export is
     * a document the user can read and re-import, not a copy of the ORM.
     */
    private static Map<String, Object> toApplication(Application a) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", a.getId() == null ? null : a.getId().toString());
        row.put("title", a.getTitle());
        row.put("company_name", a.getCompanyName());
        row.put("status", a.getStatus());
        row.put("notes", a.getNotes());
        row.put("offer_compensation", a.getOfferCompensation());
        row.put("rejection_reason", a.getRejectionReason());
        if (a.getAppliedAt() != null) {
            row.put("applied_at", a.getAppliedAt().toString());
        }
        if (a.getReminderAt() != null) {
            row.put("reminder_at", a.getReminderAt().toString());
        }
        if (a.getCreatedAt() != null) {
            row.put("created_at", a.getCreatedAt().toString());
        }
        if (a.getUpdatedAt() != null) {
            row.put("updated_at", a.getUpdatedAt().toString());
        }
        return row;
    }

    /**
     * One stored growth run. The report is the engine's own answer, carried
     * verbatim — a second copy of its shape here would drift from the engine
     * that produces it.
     */
    private static Map<String, Object> toGrowthPlan(GrowthPlan p) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", p.getId() == null ? null : p.getId().toString());
        row.put("target_role", p.getTargetRole());
        row.put("coverage", p.getCoverage());
        row.put("report", p.getReport());
        if (p.getCreatedAt() != null) {
            row.put("created_at", p.getCreatedAt().toString());
        }
        return row;
    }

    /**
     * One note the reader typed.
     *
     * The bundle's snake_case convention, like every other section: the export
     * is a document a person can read, not a copy of the ORM.
     */
    private static Map<String, Object> toNote(UserNote n) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", n.getId() == null ? null : n.getId().toString());
        row.put("title", n.getTitle());
        row.put("content", n.getContent());
        row.put("tags", n.getTags());
        if (n.getCreatedAt() != null) {
            row.put("created_at", n.getCreatedAt().toString());
        }
        if (n.getUpdatedAt() != null) {
            row.put("updated_at", n.getUpdatedAt().toString());
        }
        return row;
    }

    /**
     * One person in the reader's networking circle.
     *
     * The row is thin on purpose -- a name and where the reader knows them from
     * -- so the export is thin in the same way, and the note they wrote about
     * the person travels with it.
     */
    private static Map<String, Object> toContact(Contact c) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", c.getId() == null ? null : c.getId().toString());
        row.put("name", c.getName());
        row.put("role", c.getRole());
        row.put("company", c.getCompany());
        row.put("relation", c.getRelation());
        row.put("email", c.getEmail());
        row.put("notes", c.getNotes());
        if (c.getLastTouchAt() != null) {
            row.put("last_touch_at", c.getLastTouchAt().toString());
        }
        if (c.getCreatedAt() != null) {
            row.put("created_at", c.getCreatedAt().toString());
        }
        if (c.getUpdatedAt() != null) {
            row.put("updated_at", c.getUpdatedAt().toString());
        }
        return row;
    }

    /**
     * One chat as the bundle carries it: the conversation's own fields and
     * its transcript below them.
     */
    private static Map<String, Object> toConversation(Conversation c,
                                                      List<Map<String, Object>> messages) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", c.getId() == null ? null : c.getId().toString());
        row.put("title", c.getTitle());
        row.put("context", c.getContext());
        if (c.getCreatedAt() != null) {
            row.put("created_at", c.getCreatedAt().toString());
        }
        if (c.getUpdatedAt() != null) {
            row.put("updated_at", c.getUpdatedAt().toString());
        }
        row.put("messages", messages);
        return row;
    }

    /**
     * One message in the transcript. The run pointer is deliberately absent:
     * an activity run is bookkeeping that does not travel, and an id pointing
     * at a run the target does not have would be a dead link the restore
     * wrote on purpose.
     */
    private static Map<String, Object> toMessage(Message m) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", m.getId() == null ? null : m.getId().toString());
        row.put("role", m.getRole());
        row.put("content", m.getContent());
        row.put("artifacts", m.getArtifacts());
        row.put("sources", m.getSources());
        row.put("actions", m.getActions());
        if (m.getCreatedAt() != null) {
            row.put("created_at", m.getCreatedAt().toString());
        }
        return row;
    }

    /**
     * One saved search as the bundle carries it: the name the reader gave the
     * question and the board's own criteria.
     *
     * <p>The criteria travel as the map they are, not as the fields this
     * service happens to know: the board grows filters more often than this
     * table should need a change, and a restore that dropped the one it did
     * not recognize would bring back a different question.
     */
    private static Map<String, Object> toSavedSearch(SavedSearch s) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", s.getId() == null ? null : s.getId().toString());
        row.put("name", s.getName());
        row.put("criteria", s.getCriteria());
        if (s.getCreatedAt() != null) {
            row.put("created_at", s.getCreatedAt().toString());
        }
        if (s.getUpdatedAt() != null) {
            row.put("updated_at", s.getUpdatedAt().toString());
        }
        return row;
    }

    /**
     * One ingestion feed as the bundle carries it: the source's name, its
     * address, its label and whether the sweep is still pointed at it.
     *
     * <p>The URL is configuration rather than a secret -- the anonymized
     * bundle keeps it, because redacting a source hides nothing about a
     * person while dropping the row would break the restore's counts.
     */
    private static Map<String, Object> toIngestionFeed(IngestionFeed f) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", f.getId() == null ? null : f.getId().toString());
        row.put("name", f.getName());
        row.put("url", f.getUrl());
        row.put("source", f.getSource());
        row.put("enabled", f.isEnabled());
        if (f.getCreatedAt() != null) {
            row.put("created_at", f.getCreatedAt().toString());
        }
        if (f.getUpdatedAt() != null) {
            row.put("updated_at", f.getUpdatedAt().toString());
        }
        return row;
    }

    /**
     * The profile row as the bundle spells it.
     *
     * <p>The bundle's profile is the ai-service's own read of {@code user_profiles}
     * -- a {@code SELECT *} of the same table, in the same snake_case. The restore's
     * {@code existing} half has to answer with the same spelling, or the engine
     * would read one field name it has and one it has not as two different rows.
     */
    static Map<String, Object> toProfile(com.careeros.auth.entity.UserProfile p) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", p.getId() == null ? null : p.getId().toString());
        row.put("user_id", p.getUserId() == null ? null : p.getUserId().toString());
        row.put("headline", p.getHeadline());
        row.put("summary", p.getSummary());
        row.put("location", p.getLocation());
        row.put("years_experience", p.getYearsExperience());
        row.put("target_roles", p.getTargetRoles());
        row.put("target_locations", p.getTargetLocations());
        row.put("links", p.getLinks());
        row.put("work_authorization", p.getWorkAuthorization());
        row.put("preferences", p.getPreferences());
        // The two stamps are omitted rather than read: the entity has the
        // columns but no getters, and the engine's comparison is over the
        // fields the restore writes -- which is the point of the shape.
        return row;
    }
}
