package com.careeros.application.service;

import com.careeros.application.dto.ApplicationDtos.ApplicationItem;
import com.careeros.application.dto.ApplicationDtos.CreateApplicationRequest;
import com.careeros.application.dto.ApplicationDtos.ReorderRequest;
import com.careeros.application.dto.ApplicationDtos.TimelineEvent;
import com.careeros.application.dto.ApplicationDtos.UpdateApplicationRequest;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.PageDTO;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
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

    public ApplicationService(ApplicationRepository applications, ApplicationEventRepository events,
                              JobRepository jobs, CompanyRepository companies) {
        this.applications = applications;
        this.events = events;
        this.jobs = jobs;
        this.companies = companies;
    }

    @Transactional(readOnly = true)
    public PageDTO<ApplicationItem> list(UUID userId, String status, Pageable pageable) {
        var page = (status == null || status.isBlank())
                ? applications.findByUserIdOrderByUpdatedAtDesc(userId, pageable)
                : applications.findByUserIdAndStatusOrderByPositionAsc(userId, status, pageable);
        return PageDTO.from(page, ApplicationService::toItem);
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
        return toItem(app);
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
        }
        return toItem(applications.save(app));
    }

    @Transactional
    public ApplicationItem reorder(UUID userId, UUID id, ReorderRequest request) {
        Application app = require(userId, id);
        if (request.status() != null && !request.status().isBlank()) {
            validateStatus(request.status());
            applyStatusChange(app, request.status());
        }
        app.setPosition(request.position());
        return toItem(applications.save(app));
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

    public static ApplicationItem toItem(Application a) {
        return new ApplicationItem(a.getId(), a.getJobId(), a.getCompanyId(), a.getTitle(),
                a.getCompanyName(), a.getStatus(), a.getPosition(), a.getNotes(), a.getReminderAt(),
                a.getResumeVersionId(), a.getJdId(), a.getMatchId(), a.getAppliedAt(),
                a.getCreatedAt(), a.getUpdatedAt());
    }
}
