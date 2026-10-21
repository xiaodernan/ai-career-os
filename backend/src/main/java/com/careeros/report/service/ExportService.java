package com.careeros.report.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.entity.GrowthPlan;
import com.careeros.ai.repository.GrowthPlanRepository;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.Paging;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.UserNoteRepository;
import com.careeros.network.entity.Contact;
import com.careeros.network.repository.ContactRepository;
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
 * service reads the four the BACKEND owns — {@code applications},
 * {@code growth_plans}, {@code notes} and {@code contacts} — and hands them over.
 * The hash is still computed in one place (the ai-service), so a bundle has one
 * hashing rule rather than one per producer, and a bundle without the pipeline the
 * candidate actually worked is a bundle of their reading list and nothing else.
 *
 * <p>The notes and the contacts are not a nicety: they are the reader's own words
 * and the people they know. "Your data" that leaves out the two tables the reader
 * typed into is not their data.
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

    public ExportService(AiServiceClient aiService, ApplicationRepository applications,
                          GrowthPlanRepository growthPlans, UserNoteRepository notes,
                          ContactRepository contacts) {
        this.aiService = aiService;
        this.applications = applications;
        this.growthPlans = growthPlans;
        this.notes = notes;
        this.contacts = contacts;
    }

    /**
     * The export bundle for the caller: the ai-service's six sections plus the
     * backend's two, hashed together.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> exportBundle(UUID userId, boolean anonymized) {
        return aiService.exportBundle(userId, anonymized, backendSections(userId));
    }

    /** The sections the backend owns, in the bundle's own shape. */
    private Map<String, Object> backendSections(UUID userId) {
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
        return sections;
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
}
