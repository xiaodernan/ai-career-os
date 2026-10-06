package com.careeros.application.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.application.dto.ApplicationDtos.ReorderRequest;
import com.careeros.application.dto.ApplicationDtos.UpdateApplicationRequest;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import java.time.OffsetDateTime;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/**
 * Audited status transitions: the {@code from} value in the timeline event must be the
 * status the application held *before* the change. Plain Mockito (no DB / no Spring context)
 * captures the {@link ApplicationEvent} handed to the event repository.
 */
class ApplicationServiceTest {

    private final UUID userId = UUID.randomUUID();
    private final UUID appId = UUID.randomUUID();

    private ApplicationRepository applications;
    private ApplicationEventRepository events;
    private ApplicationService service;

    @BeforeEach
    void setUp() {
        applications = mock(ApplicationRepository.class);
        events = mock(ApplicationEventRepository.class);
        service = new ApplicationService(applications, events,
                mock(JobRepository.class), mock(CompanyRepository.class));
        when(applications.save(any(Application.class))).thenAnswer(i -> i.getArgument(0));
    }

    private Application existing(String status) {
        Application app = new Application();
        app.setUserId(userId);
        app.setStatus(status);
        when(applications.findByIdAndUserId(appId, userId)).thenReturn(Optional.of(app));
        return app;
    }

    private ApplicationEvent savedEvent() {
        ArgumentCaptor<ApplicationEvent> cap = ArgumentCaptor.forClass(ApplicationEvent.class);
        verify(events).save(cap.capture());
        return cap.getValue();
    }

    @Test
    void updateLogsTheRealPriorStatusNotTheOverwrittenOne() {
        Application app = existing("interview");

        service.update(userId, appId, new UpdateApplicationRequest("offer", null, null, null, null, null, null));

        ApplicationEvent evt = savedEvent();
        assertThat(evt.getKind()).isEqualTo("status");
        // Regression: `from` used to read getStatus() AFTER setStatus, logging "offer -> offer".
        assertThat(evt.getPayload())
                .containsEntry("from", "interview")
                .containsEntry("to", "offer");
        assertThat(app.getStatus()).isEqualTo("offer");
    }

    @Test
    void updateWithSameStatusEmitsNoTransitionEvent() {
        existing("offer");

        service.update(userId, appId,
                new UpdateApplicationRequest("offer", null, "strong candidate", null, null, null, null));

        // Only the note event is written; a same-status change must not fake a transition.
        assertThat(savedEvent().getKind()).isEqualTo("note");
    }

    @Test
    void reorderAlsoLogsTheRealPriorStatus() {
        Application app = existing("applied");

        service.reorder(userId, appId, new ReorderRequest(2, "interview"));

        assertThat(savedEvent().getPayload())
                .containsEntry("from", "applied")
                .containsEntry("to", "interview");
        assertThat(app.getPosition()).isEqualTo(2);
    }

    @Test
    void reorderIntoAppliedStampsAppliedAtLikeTheUpdatePathDoes() {
        Application app = existing("saved");
        assertThat(app.getAppliedAt()).isNull();

        // The kanban drag is the primary way a card reaches "applied"; it must maintain
        // the derived applied_at column just like create/update, or reports lose the date.
        service.reorder(userId, appId, new ReorderRequest(0, "applied"));

        assertThat(app.getStatus()).isEqualTo("applied");
        assertThat(app.getAppliedAt()).isNotNull();
    }

    @Test
    void reorderIntoAppliedKeepsTheOriginalAppliedAt() {
        Application app = existing("rejected");
        OffsetDateTime first = OffsetDateTime.parse("2020-01-02T03:04:05Z");
        app.setAppliedAt(first);

        // Re-applying must not overwrite the first application date (null-guarded stamp).
        service.reorder(userId, appId, new ReorderRequest(0, "applied"));

        assertThat(app.getStatus()).isEqualTo("applied");
        assertThat(app.getAppliedAt()).isEqualTo(first);
    }

    @Test
    void clearingAReminderRemovesItAndAuditsTheChange() {
        Application app = existing("interview");
        app.setReminderAt(OffsetDateTime.parse("2026-06-01T09:00:00Z"));

        // A null component means "leave it alone", so deleting the reminder travels as its
        // own flag; before that existed the timestamp could only ever be set, never removed.
        service.update(userId, appId, new UpdateApplicationRequest(null, null, null, null, true, null, null));

        assertThat(app.getReminderAt()).isNull();
        ApplicationEvent evt = savedEvent();
        assertThat(evt.getKind()).isEqualTo("reminder");
        assertThat(evt.getPayload()).containsEntry("cleared", true);
    }

    @Test
    void clearingWhenThereWasNoReminderWritesNothing() {
        Application app = existing("saved");

        service.update(userId, appId, new UpdateApplicationRequest(null, null, null, null, true, null, null));

        // The same no-op rule the status transition follows: nothing changed, so no audit row.
        assertThat(app.getReminderAt()).isNull();
        verify(events, never()).save(any(ApplicationEvent.class));
    }

    @Test
    void aReminderAndAClearInTheSamePatchKeepTheNewReminder() {
        Application app = existing("saved");
        OffsetDateTime at = OffsetDateTime.parse("2026-07-01T09:00:00Z");

        service.update(userId, appId, new UpdateApplicationRequest(null, null, null, at, true, null, null));

        assertThat(app.getReminderAt()).isEqualTo(at);
    }
}
