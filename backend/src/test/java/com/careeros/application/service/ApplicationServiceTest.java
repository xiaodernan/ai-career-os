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
import com.careeros.application.dto.ApplicationDtos.ApplicationItem;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

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
    private ApplicationLetterRepository letters;
    private ApplicationService service;

    @BeforeEach
    void setUp() {
        applications = mock(ApplicationRepository.class);
        events = mock(ApplicationEventRepository.class);
        letters = mock(ApplicationLetterRepository.class);
        service = new ApplicationService(applications, events,
                mock(JobRepository.class), mock(CompanyRepository.class), letters);
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

    /**
     * The job page asks one posting's rows so it can say "already in the pipeline" before the
     * reader presses Add a second time. The narrow query must be the one that runs -- falling
     * back to the whole board and filtering in memory would scan pages the posting is not on.
     */
    @Test
    void listNarrowsToThePostingWhenAJobIdIsGiven() {
        UUID jobId = UUID.randomUUID();
        Pageable pageable = PageRequest.of(0, 1);
        when(applications.findPage(userId, "", jobId, "", pageable))
                .thenReturn(Page.empty(pageable));

        var page = service.list(userId, null, jobId, null, pageable);

        assertThat(page.items()).isEmpty();
        verify(applications).findPage(userId, "", jobId, "", pageable);
        verify(applications, never()).findByUserIdOrderByUpdatedAtDescIdAsc(any(), any());
    }

    /** A status alongside the posting keeps both narrowings instead of silently dropping one. */
    @Test
    void listKeepsTheStatusWhenItComesWithAPosting() {
        UUID jobId = UUID.randomUUID();
        Pageable pageable = PageRequest.of(0, 1);
        when(applications.findColumnPage(userId, "applied", jobId, "", pageable))
                .thenReturn(Page.empty(pageable));

        var page = service.list(userId, "applied", jobId, null, pageable);

        assertThat(page.items()).isEmpty();
        verify(applications).findColumnPage(userId, "applied", jobId, "", pageable);
        verify(applications, never()).findPage(any(), any(), any(), any(), any());
    }

    /**
     * 70.1: the reader's word is data, so it is normalised once per request rather than per row, and
     * SQL never sees the spaces the box kept or the case the keyboard was in.
     */
    @Test
    void theNeedleArrivesTrimmedAndLowerCase() {
        Pageable pageable = PageRequest.of(0, 50);
        when(applications.findPage(userId, "", null, "acme_data", pageable))
                .thenReturn(Page.empty(pageable));

        service.list(userId, null, null, "  AcME_DaTa ", pageable);

        verify(applications).findPage(userId, "", null, "acme_data", pageable);
    }

    /**
     * A blank box is the board itself, not an empty room: 58.1's company branch takes a different
     * query, but this route has filters beside the box that must keep applying either way, so the
     * emptiness travels as the query's own escape value and the column stays narrowed.
     */
    @Test
    void aBlankBoxIsNoFilterRatherThanAnEmptyBoard() {
        Pageable pageable = PageRequest.of(0, 50);
        when(applications.findColumnPage(userId, "interview", null, "", pageable))
                .thenReturn(Page.empty(pageable));

        service.list(userId, "interview", null, "   ", pageable);

        verify(applications).findColumnPage(userId, "interview", null, "", pageable);
    }

    /** A record so the grouped-count projection has something to answer with. */
    private record Total(UUID getApplicationId, long getTotal)
            implements ApplicationLetterRepository.LetterTotal {
    }

    /**
     * The board asks for every card's letter total at once. One grouped read answers the whole
     * page; a card with no letters is simply absent from it and must still read zero, not null.
     */
    @Test
    void theListCarriesEachCardLetterCountFromOneGroupedRead() {
        UUID otherId = UUID.randomUUID();
        Application withLetters = mock(Application.class);
        Application without = mock(Application.class);
        when(withLetters.getId()).thenReturn(appId);
        when(without.getId()).thenReturn(otherId);
        when(applications.findPage(userId, "", null, "", PageRequest.of(0, 50)))
                .thenReturn(new PageImpl<>(List.of(withLetters, without), PageRequest.of(0, 50), 2));
        when(letters.countByUserAndApplicationIds(userId, List.of(appId, otherId)))
                .thenReturn(List.of(new Total(appId, 4)));

        var page = service.list(userId, null, null, null, PageRequest.of(0, 50));

        assertThat(page.items()).extracting(ApplicationItem::letters).containsExactly(4, 0);
        verify(letters).countByUserAndApplicationIds(userId, List.of(appId, otherId));
    }

    @Test
    void aSingleReadCountsOnlyThisApplicationsLetters() {
        Application app = mock(Application.class);
        when(app.getId()).thenReturn(appId);
        when(applications.findByIdAndUserId(appId, userId)).thenReturn(Optional.of(app));
        when(letters.countByApplicationIdAndUserId(appId, userId)).thenReturn(5L);

        ApplicationItem item = service.get(userId, appId);

        assertThat(item.letters()).isEqualTo(5);
    }
}
