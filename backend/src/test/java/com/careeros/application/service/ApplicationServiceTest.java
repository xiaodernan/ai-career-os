package com.careeros.application.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
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

        service.update(userId, appId, new UpdateApplicationRequest("offer", null, null, null));

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

        service.update(userId, appId, new UpdateApplicationRequest("offer", null, "strong candidate", null));

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
}
