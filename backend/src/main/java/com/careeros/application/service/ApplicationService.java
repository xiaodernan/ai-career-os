package com.careeros.application.service;

import com.careeros.application.dto.ApplicationDtos.ApplicationItem;
import com.careeros.application.dto.ApplicationDtos.CreateApplicationRequest;
import com.careeros.application.dto.ApplicationDtos.ReorderRequest;
import com.careeros.application.dto.ApplicationDtos.TimelineEvent;
import com.careeros.application.dto.ApplicationDtos.UpdateApplicationRequest;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Kanban applications: statuses are the columns; every transition is audited as an event. */
@Service
public class ApplicationService {

    public static final Set<String> STATUSES =
            Set.of("saved", "applied", "oa", "interview", "final_round", "offer", "rejected");

    private final ApplicationRepository applications;
    private final ApplicationEventRepository events;
    private final JobRepository jobs;
    private final CompanyRepository companies;
    private final ApplicationLetterRepository letters;

    public ApplicationService(ApplicationRepository applications, ApplicationEventRepository events,
                              JobRepository jobs, CompanyRepository companies,
                              ApplicationLetterRepository letters) {
        this.applications = applications;
        this.events = events;
        this.jobs = jobs;
        this.companies = companies;
        this.letters = letters;
    }

    @Transactional(readOnly = true)
    public PageDTO<ApplicationItem> list(UUID userId, String status, UUID jobId, Pageable pageable) {
        // `jobId` is the reading side of "did I already apply to this posting": the job page asks
        // one posting's rows and opens the newest, instead of scanning pages the way a title
        // search would have to. A status still narrows the same posting when both are given.
        boolean hasStatus = status != null && !status.isBlank();
        var page = jobId != null
                ? (hasStatus
                        ? applications.findByUserIdAndJobIdAndStatusOrderByPositionAscIdAsc(
                                userId, jobId, status, pageable)
                        : applications.findByUserIdAndJobIdOrderByUpdatedAtDescIdAsc(
                                userId, jobId, pageable))
                : (hasStatus
                        ? applications.findByUserIdAndStatusOrderByPositionAscIdAsc(
                                userId, status, pageable)
                        : applications.findByUserIdOrderByUpdatedAtDescIdAsc(userId, pageable));
        // The card's fourth artifact is a count (53.1), and the board must not spend one request
        // per card to learn it: one grouped read answers the whole page, and an application with
        // no letters is simply absent from the map.
        List<UUID> ids = page.getContent().stream().map(Application::getId).toList();
        Map<UUID, Long> letterTotals = new HashMap<>();
        for (ApplicationLetterRepository.LetterTotal row : ids.isEmpty()
                ? List.<ApplicationLetterRepository.LetterTotal>of()
                : letters.countByUserAndApplicationIds(userId, ids)) {
            letterTotals.put(row.getApplicationId(), row.getTotal());
        }
        return PageDTO.from(page, a -> toItem(a, letterTotals.getOrDefault(a.getId(), 0L).intValue()));
    }

    @Transactional
    public ApplicationItem create(UUID userId, CreateApplicationRequest request) {
        String status = request.status() == null || request.status().isBlank() ? "saved" : request.status();
        validateStatus(status);
        Application app = new Application();
        app.setUserId(userId);
        app.setTitle(request.title().trim());
        app.setStatus(status);
        app.setNotes(request.notes());
        app.setReminderAt(request.reminderAt());
        app.setResumeVersionId(request.resumeVersionId());
        app.setJdId(request.jdId());
        app.setMatchId(request.matchId());
        if ("applied".equals(status)) {
            app.setAppliedAt(OffsetDateTime.now());
        }
        if (request.jobId() != null) {
            Job job = jobs.findById(request.jobId())
                    .orElseThrow(() -> new ApiException(ApiErrorCode.JOB_NOT_FOUND, "Job not found"));
            app.setJobId(job.getId());
            app.setCompanyId(job.getCompanyId());
            app.setTitle(request.title() == null || request.title().isBlank()
                    ? job.getTitle() : request.title().trim());
            companies.findById(job.getCompanyId()).ifPresent(c -> app.setCompanyName(c.getName()));
        } else {
            if (request.companyId() != null) {
                Company company = companies.findById(request.companyId())
                        .orElseThrow(() -> new ApiException(ApiErrorCode.COMPANY_NOT_FOUND,
                                "Company not found"));
                app.setCompanyId(company.getId());
                app.setCompanyName(company.getName());
            }
            if (request.companyName() != null) {
                app.setCompanyName(request.companyName());
            }
        }
        app.setPosition((int) applications.countByUserIdAndStatus(userId, status));
        applications.save(app);
        writeEvent(app, "status", Map.of("to", status));
        // A brand-new application cannot hold a letter yet; saying so costs no query.
        return toItem(app, 0);
    }

    @Transactional
    public ApplicationItem update(UUID userId, UUID id, UpdateApplicationRequest request) {
        Application app = require(userId, id);
        if (request.status() != null && !request.status().isBlank()) {
            validateStatus(request.status());
            applyStatusChange(app, request.status());
        }
        if (request.position() != null) {
            app.setPosition(request.position());
        }
        if (request.note() != null) {
            app.setNotes(request.note());
            writeEvent(app, "note", Map.of("note", request.note()));
        }
        if (request.reminderAt() != null) {
            app.setReminderAt(request.reminderAt());
            writeEvent(app, "reminder", Map.of("reminder_at", request.reminderAt().toString()));
        } else if (Boolean.TRUE.equals(request.clearReminderAt()) && app.getReminderAt() != null) {
            // A reminder nobody can delete is permanent dashboard noise: the attention query
            // counts `reminder_at <= now()`, so a stale one nags forever. Only an actual change
            // is audited, the same rule the status transition above follows.
            app.setReminderAt(null);
            writeEvent(app, "reminder", Map.of("cleared", true));
        }
        // Terminal outcomes are optional but, once set, clearable by an empty string:` the
        // PATCH contract says a null component means "leave it alone", so an empty string is the
        // only way a caller can say "set it back to nothing" for these two. Only an actual change
        // is audited, and each keeps its own event so the timeline says what moved.
        if (request.offerCompensation() != null) {
            String next = request.offerCompensation().isBlank() ? null : request.offerCompensation();
            if (!Objects.equals(next, app.getOfferCompensation())) {
                app.setOfferCompensation(next);
                writeEvent(app, "outcome", Map.of("field", "offer_compensation"));
            }
        }
        if (request.rejectionReason() != null) {
            String next = request.rejectionReason().isBlank() ? null : request.rejectionReason();
            if (!Objects.equals(next, app.getRejectionReason())) {
                app.setRejectionReason(next);
                writeEvent(app, "outcome", Map.of("field", "rejection_reason"));
            }
        }
        return item(userId, applications.save(app));
    }

    @Transactional
    public ApplicationItem reorder(UUID userId, UUID id, ReorderRequest request) {
        Application app = require(userId, id);
        if (request.status() != null && !request.status().isBlank()) {
            validateStatus(request.status());
            applyStatusChange(app, request.status());
        }
        app.setPosition(request.position());
        return item(userId, applications.save(app));
    }

    /**
     * Records what the user produced for one job on the application rows they already track.
     *
     * <p>The three link columns are the reason a card can say which resume, JD analysis and match
     * stand behind it, and they are minted by the match, tailor and JD-analysis routes — which run
     * before the tracker row exists, or long after it, but never through it. Nothing else can fill
     * them.
     *
     * <p>A null argument means "this action did not produce that id" and leaves the column alone:
     * tailoring a job must not clear the match the same row already carries. Only a real change is
     * written, so re-running a match is not a write per call, and the return value is the number of
     * rows that moved.
     *
     * <p>No audit event. {@code ApplicationEvent} rows are the user-visible transitions the timeline
     * renders — status, note, reminder — and an id appearing beside a row is not one of them; the
     * dialog shows the links themselves.
     */
    @Transactional
    public int linkJobActivity(UUID userId, UUID jobId, UUID resumeVersionId, UUID jdId, UUID matchId) {
        if (jobId == null || (resumeVersionId == null && jdId == null && matchId == null)) {
            return 0;
        }
        int changed = 0;
        for (Application app : applications.findByUserIdAndJobId(userId, jobId)) {
            boolean dirty = false;
            if (resumeVersionId != null && !resumeVersionId.equals(app.getResumeVersionId())) {
                app.setResumeVersionId(resumeVersionId);
                dirty = true;
            }
            if (jdId != null && !jdId.equals(app.getJdId())) {
                app.setJdId(jdId);
                dirty = true;
            }
            if (matchId != null && !matchId.equals(app.getMatchId())) {
                app.setMatchId(matchId);
                dirty = true;
            }
            if (dirty) {
                applications.save(app);
                changed++;
            }
        }
        return changed;
    }

    @Transactional(readOnly = true)
    public List<TimelineEvent> timeline(UUID userId, UUID id) {
        require(userId, id);
        return events.findByApplicationIdOrderByCreatedAtDesc(id).stream()
                .map(e -> new TimelineEvent(e.getId(), e.getKind(), e.getPayload(), e.getCreatedAt()))
                .toList();
    }

    @Transactional
    public void delete(UUID userId, UUID id) {
        applications.delete(require(userId, id));
    }

    public Application require(UUID userId, UUID id) {
        return applications.findByIdAndUserId(id, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.APPLICATION_NOT_FOUND,
                        "Application not found"));
    }

    /**
     * The one place a status transition is applied, so every write path (PATCH update and
     * the kanban reorder) maintains derived columns and audit history identically. A
     * same-status call is a no-op — it must not fake a transition event.
     */
    private void applyStatusChange(Application app, String to) {
        if (to.equals(app.getStatus())) {
            return;
        }
        String from = app.getStatus();
        app.setStatus(to);
        if ("applied".equals(to) && app.getAppliedAt() == null) {
            app.setAppliedAt(OffsetDateTime.now());
        }
        writeEvent(app, "status", Map.of("from", from, "to", to));
    }

    private void writeEvent(Application app, String kind, Map<String, Object> payload) {
        ApplicationEvent event = new ApplicationEvent();
        event.setApplicationId(app.getId());
        event.setUserId(app.getUserId());
        event.setKind(kind);
        event.setPayload(payload);
        events.save(event);
    }

    private static void validateStatus(String status) {
        if (!STATUSES.contains(status)) {
            throw new ApiException(ApiErrorCode.INVALID_STATUS, "Unknown application status: " + status);
        }
    }

    /** One application with its letter total read for this caller. */
    @Transactional(readOnly = true)
    public ApplicationItem get(UUID userId, UUID id) {
        return item(userId, require(userId, id));
    }

    /**
     * The stage of each card a page of rehearsals names (57.4), in one read.
     *
     * <p>The interview list draws a stage badge per row, and a per-row lookup
     * would be one query per rehearsal -- the exact shape the digest read
     * avoids. Scoped by the caller like every other read here: a card the page
     * names but this account does not own is simply absent from the map, and
     * the row falls back to no badge.
     */
    @Transactional(readOnly = true)
    public Map<UUID, String> stagesOf(UUID userId, Collection<UUID> ids) {
        if (ids == null || ids.isEmpty()) {
            return Map.of();
        }
        Map<UUID, String> stages = new HashMap<>();
        for (Application card : applications.findByUserIdAndIdIn(userId, ids)) {
            stages.put(card.getId(), card.getStatus());
        }
        return stages;
    }

    /** The one place a single application's letter total is read, scoped to its owner. */
    private ApplicationItem item(UUID userId, Application app) {
        return toItem(app, (int) letters.countByApplicationIdAndUserId(app.getId(), userId));
    }

    public static ApplicationItem toItem(Application a) {
        return toItem(a, 0);
    }

    public static ApplicationItem toItem(Application a, int letters) {
        return new ApplicationItem(a.getId(), a.getJobId(), a.getCompanyId(), a.getTitle(),
                a.getCompanyName(), a.getStatus(), a.getPosition(), a.getNotes(), a.getReminderAt(),
                a.getResumeVersionId(), a.getJdId(), a.getMatchId(), a.getAppliedAt(),
                a.getCreatedAt(), a.getUpdatedAt(), a.getOfferCompensation(),
                a.getRejectionReason(), letters);
    }
}
