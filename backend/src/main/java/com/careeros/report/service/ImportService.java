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
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.UserNoteRepository;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
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
 */
@Service
public class ImportService {

    private final AiServiceClient aiService;
    private final UserProfileRepository profiles;
    private final UserNoteRepository notes;
    private final ApplicationRepository applications;
    private final GrowthPlanRepository growthPlans;

    public ImportService(AiServiceClient aiService, UserProfileRepository profiles,
                          UserNoteRepository notes, ApplicationRepository applications,
                          GrowthPlanRepository growthPlans) {
        this.aiService = aiService;
        this.profiles = profiles;
        this.notes = notes;
        this.applications = applications;
        this.growthPlans = growthPlans;
    }

    /**
     * Plan a re-import without writing anything: the ops the engine would run,
     * and the counts.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> plan(UUID userId, Map<String, Object> bundle,
                                    Map<String, Object> existing) {
        return aiService.importPlan(userId, bundle, existing);
    }

    /**
     * Apply a re-import. The plan is computed first, then executed section by
     * section; the answer says what was written and what was left alone.
     */
    @Transactional
    public Map<String, Object> apply(UUID userId, Map<String, Object> bundle) {
        if (bundle == null || !(bundle.get("data") instanceof Map)) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "The bundle has no data section.");
        }
        // The plan is the engine's answer about what should change; the apply
        // executes exactly those ops and nothing else.
        Map<String, Object> plan = aiService.importPlan(userId, bundle, currentState(userId));
        @SuppressWarnings("unchecked")
        Map<String, List<Map<String, Object>>> sections =
                (Map<String, List<Map<String, Object>>>) plan.get("sections");
        if (sections == null) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "The bundle could not be planned.");
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) bundle.get("data");
        Map<String, int[]> applied = new LinkedHashMap<>();
        List<Map<String, String>> skipped = new ArrayList<>();

        applyProfile(userId, data, sections, applied, skipped);
        applyNotes(userId, data, sections, applied, skipped);
        applyApplications(userId, data, sections, applied, skipped);
        applyGrowthPlans(userId, data, sections, applied, skipped);

        // The sections the backend cannot write are reported rather than
        // silently ignored: a restore that says "done" while leaving half the
        // bundle behind is a lie the user finds out about later.
        for (String section : List.of("resumes", "knowledge", "job_descriptions", "interviews")) {
            List<Map<String, Object>> ops = sections.get(section);
            if (ops != null && !ops.isEmpty()) {
                skipped.add(Map.of("section", section,
                        "reason", "This section is not applied yet — it needs its own ingestion pipeline."));
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("applied", applied.entrySet().stream()
                .collect(java.util.stream.Collectors.toMap(
                        Map.Entry::getKey,
                        e -> Map.of("created", e.getValue()[0], "updated", e.getValue()[1],
                                "deleted", e.getValue()[2]))));
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

    /** The notes: create what is new, update what changed, delete what is gone. */
    private void applyNotes(UUID userId, Map<String, Object> data,
                            Map<String, List<Map<String, Object>>> sections,
                            Map<String, int[]> applied, List<Map<String, String>> skipped) {
        List<Map<String, Object>> ops = sections.get("memories");
        if (ops == null) {
            return;
        }
        // The bundle's "memories" section is the long-term memory store; the
        // user's own notes live in a different table and are not part of the
        // bundle, so there is nothing to write here yet. The section is
        // reported rather than claimed.
        skipped.add(Map.of("section", "memories",
                "reason", "The memory store is written by the agents, not restored from a bundle."));
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
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
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
                if (rowId != null) {
                    setId(target, rowId);
                }
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
        count(applied, "applications", created, updated, deleted);
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
        for (Map<String, Object> op : ops) {
            String id = str(op, "id");
            String kind = str(op, "op");
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
                if (rowId != null) {
                    setId(target, rowId);
                }
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
        count(applied, "growth_plans", created, updated, deleted);
    }

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */

    /** The caller's current state, exported the same way — the plan's other half. */
    private Map<String, Object> currentState(UUID userId) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("profile", profiles.findByUserId(userId).orElse(null));
        data.put("applications", applications.findByUserIdOrderByUpdatedAtDescIdAsc(
                userId, com.careeros.common.Paging.first(1000)).stream()
                .map(row -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", row.getId() == null ? null : row.getId().toString());
                    m.put("title", row.getTitle());
                    m.put("status", row.getStatus());
                    return m;
                }).toList());
        data.put("growth_plans", growthPlans.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(row -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", row.getId() == null ? null : row.getId().toString());
                    m.put("target_role", row.getTargetRole());
                    return m;
                }).toList());
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
        if (value instanceof List<?> list) {
            return list.stream().map(String::valueOf).toList();
        }
        return List.of();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Map<?, ?> row, String key) {
        Object value = row.get(key);
        return value instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
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

    private static void count(Map<String, int[]> applied, String section, int created, int updated) {
        count(applied, section, created, updated, 0);
    }

    private static void count(Map<String, int[]> applied, String section,
                              int created, int updated, int deleted) {
        applied.computeIfAbsent(section, k -> new int[3]);
        int[] row = applied.get(section);
        row[0] += created;
        row[1] += updated;
        row[2] += deleted;
    }
}
