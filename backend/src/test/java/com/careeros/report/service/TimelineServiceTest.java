package com.careeros.report.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.entity.Application;
import com.careeros.application.entity.ApplicationEvent;
import com.careeros.application.repository.ApplicationEventRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.interview.entity.InterviewSession;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.entity.JobMatch;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.knowledge.entity.UserNote;
import com.careeros.knowledge.repository.UserNoteRepository;
import com.careeros.network.entity.Contact;
import com.careeros.network.repository.ContactRepository;
import com.careeros.resume.entity.ResumeVersion;
import com.careeros.resume.repository.ResumeVersionRepository;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;

/**
 * The timeline bridge hands one account's own rows to the engine (Epic 81).
 *
 * <p>What these cases pin is the row builder: every event the bridge builds
 * carries the engine's own five fields, the reader's own {@code userId} never
 * leaks into the payload, and the merge the caller hears is the engine's, not
 * a sort this service performs. The rows here are stamped by the tests the way
 * Hibernate stamps them, because the timestamps are the whole point.
 */
class TimelineServiceTest {

    private static final UUID USER = UUID.fromString("6b0178a0-d352-09c3-ea65-8f107bd28d01");

    private AiServiceClient ai;
    private ApplicationRepository applications;
    private ApplicationEventRepository applicationEvents;
    private UserNoteRepository notes;
    private ContactRepository contacts;
    private ResumeVersionRepository resumeVersions;
    private JobMatchRepository matches;
    private InterviewSessionRepository interviews;
    private TimelineService service;

    @BeforeEach
    void setUp() {
        ai = mock(AiServiceClient.class);
        applications = mock(ApplicationRepository.class);
        applicationEvents = mock(ApplicationEventRepository.class);
        notes = mock(UserNoteRepository.class);
        contacts = mock(ContactRepository.class);
        resumeVersions = mock(ResumeVersionRepository.class);
        matches = mock(JobMatchRepository.class);
        interviews = mock(InterviewSessionRepository.class);
        service = new TimelineService(ai, applications, applicationEvents, notes, contacts, resumeVersions, matches, interviews);

        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(applicationEvents.findByUserIdOrderByCreatedAtDesc(eq(USER), any(Pageable.class)))
                .thenReturn(List.of());
        when(notes.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(contacts.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(resumeVersions.findByUserIdOrderByCreatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(matches.findByUserIdOrderByCreatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(interviews.findPage(eq(USER), any(), eq(""), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of()));
        when(ai.careerTimeline(eq(USER), any())).thenReturn(Map.of("timeline", List.of()));
    }

    private ApplicationEvent statusTransition(String from, String to) {
        ApplicationEvent e = new ApplicationEvent();
        e.setApplicationId(UUID.fromString("2b1c3c4e-1111-2222-3333-444444444444"));
        e.setUserId(USER);
        e.setKind("status");
        e.setPayload(Map.of("from", from, "to", to));
        org.springframework.test.util.ReflectionTestUtils.setField(e, "createdAt",
                OffsetDateTime.parse("2026-09-02T12:00:00+00:00"));
        return e;
    }

    private Application application() {
        Application a = new Application();
        a.setUserId(USER);
        a.setTitle("Backend Engineer");
        a.setCompanyName("Acme Robotics");
        a.setStatus("applied");
        a.setAppliedAt(OffsetDateTime.parse("2026-09-01T09:00:00+00:00"));
        org.springframework.test.util.ReflectionTestUtils.setField(a, "id", UUID.fromString("2b1c3c4e-1111-2222-3333-444444444444"));
        org.springframework.test.util.ReflectionTestUtils.setField(a, "createdAt",
                OffsetDateTime.parse("2026-09-01T08:00:00+00:00"));
        return a;
    }

    private UserNote note() {
        UserNote n = new UserNote();
        n.setUserId(USER);
        n.setTitle("Interview prep");
        n.setContent("Budget a week the night before.");
        n.setTags(List.of("interview", "study"));
        org.springframework.test.util.ReflectionTestUtils.setField(n, "id", UUID.fromString("3b1c3c4e-1111-2222-3333-444444444444"));
        org.springframework.test.util.ReflectionTestUtils.setField(n, "createdAt",
                OffsetDateTime.parse("2026-09-06T10:00:00+00:00"));
        return n;
    }

    private Contact contact() {
        Contact c = new Contact();
        c.setUserId(USER);
        c.setName("Ada Byron");
        c.setRelation("referrer");
        org.springframework.test.util.ReflectionTestUtils.setField(c, "id", UUID.fromString("4b1c3c4e-1111-2222-3333-444444444444"));
        org.springframework.test.util.ReflectionTestUtils.setField(c, "createdAt",
                OffsetDateTime.parse("2026-09-02T07:00:00+00:00"));
        return c;
    }

    private ResumeVersion resumeVersion() {
        ResumeVersion v = new ResumeVersion();
        v.setUserId(USER);
        v.setLabel("original");
        v.setKind("original");
        org.springframework.test.util.ReflectionTestUtils.setField(v, "id", UUID.fromString("5b1c3c4e-1111-2222-3333-444444444444"));
        org.springframework.test.util.ReflectionTestUtils.setField(v, "createdAt",
                OffsetDateTime.parse("2026-09-03T06:00:00+00:00"));
        return v;
    }

    private JobMatch match() {
        JobMatch m = new JobMatch();
        org.springframework.test.util.ReflectionTestUtils.setField(m, "userId", USER);
        org.springframework.test.util.ReflectionTestUtils.setField(m, "overall", 82.5f);
        org.springframework.test.util.ReflectionTestUtils.setField(m, "technical", 80f);
        org.springframework.test.util.ReflectionTestUtils.setField(m, "experience", 70f);
        org.springframework.test.util.ReflectionTestUtils.setField(m, "projects", 85f);
        org.springframework.test.util.ReflectionTestUtils.setField(m, "education", 90f);
        org.springframework.test.util.ReflectionTestUtils.setField(m, "id", UUID.fromString("6b1c3c4e-1111-2222-3333-444444444444"));
        org.springframework.test.util.ReflectionTestUtils.setField(m, "createdAt",
                OffsetDateTime.parse("2026-09-04T05:00:00+00:00"));
        return m;
    }

    private InterviewSession interview() {
        InterviewSession s = new InterviewSession();
        s.setUserId(USER);
        s.setMode("mixed");
        s.setStatus("active");
        s.setPositionTitle("Backend Engineer");
        s.setStartedAt(OffsetDateTime.parse("2026-09-07T04:00:00+00:00"));
        org.springframework.test.util.ReflectionTestUtils.setField(s, "id", UUID.fromString("7b1c3c4e-1111-2222-3333-444444444444"));
        return s;
    }

    @Test
    void the_status_transition_log_reaches_the_funnel_as_timeline_rows() {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(applicationEvents.findByUserIdOrderByCreatedAtDesc(eq(USER), any(Pageable.class)))
                .thenReturn(List.of(statusTransition("saved", "applied")));

        Map<String, Object> answer = service.timeline(USER);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> events = ArgumentCaptor.forClass(List.class);
        org.mockito.Mockito.verify(ai).careerTimeline(eq(USER), events.capture());
        List<Map<String, Object>> rows = events.getValue();
        // The entity row and the transition are both application events, so the reader sees both.
        Map<String, Object> transition = rows.stream()
                .filter(e -> "application".equals(e.get("kind")) && "→ applied".equals(e.get("title")))
                .findFirst().orElseThrow();
        assertThat(transition).containsEntry("refId", "2b1c3c4e-1111-2222-3333-444444444444")
                .containsEntry("summary", "saved → applied")
                .containsEntry("kind", "application")
                .containsEntry("at", "2026-09-02T12:00:00Z");
        assertThat(rows.stream().filter(e -> "application".equals(e.get("kind"))).count())
                .isEqualTo(2);
        assertThat(answer).containsEntry("timeline", List.of());
    }

    @Test
    void every_event_the_bridge_sends_carries_the_engines_own_five_fields() {
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(application())));
        when(notes.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(note())));
        when(contacts.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(contact())));
        when(resumeVersions.findByUserIdOrderByCreatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(resumeVersion())));
        when(matches.findByUserIdOrderByCreatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(match())));
        when(interviews.findPage(eq(USER), any(), eq(""), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(interview())));

        Map<String, Object> answer = service.timeline(USER);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> events = ArgumentCaptor.forClass(List.class);
        org.mockito.Mockito.verify(ai).careerTimeline(eq(USER), events.capture());
        assertThat(events.getValue()).hasSize(6);
        assertThat(events.getValue()).allSatisfy(event ->
                assertThat(event.keySet()).containsExactlyInAnyOrder("at", "kind", "title", "refId", "summary"));
        assertThat(events.getValue()).extracting(e -> e.get("kind"))
                .containsExactlyInAnyOrder("application", "note", "contact", "resume_version", "match", "interview");
        // The application travels with the reader's own company name, not a guess.
        Map<String, Object> appRow = events.getValue().stream()
                .filter(e -> "application".equals(e.get("kind"))).findFirst().orElseThrow();
        assertThat(appRow).containsEntry("title", "Backend Engineer · Acme Robotics")
                .containsEntry("summary", "status: applied")
                .containsEntry("at", "2026-09-01T09:00:00Z")
                .containsEntry("refId", "2b1c3c4e-1111-2222-3333-444444444444");
        // And the engine's answer is the body the caller hears, untouched.
        assertThat(answer).containsEntry("timeline", List.of());
    }

    @Test
    void an_account_with_nothing_answers_no_events() {
        service.timeline(USER);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> events = ArgumentCaptor.forClass(List.class);
        org.mockito.Mockito.verify(ai).careerTimeline(eq(USER), events.capture());
        assertThat(events.getValue()).isEmpty();
    }

    @Test
    void an_application_without_an_applied_at_is_dated_by_its_creation() {
        Application a = application();
        a.setAppliedAt(null);
        when(applications.findByUserIdOrderByUpdatedAtDescIdAsc(eq(USER), any(Pageable.class)))
                .thenReturn(new PageImpl<>(List.of(a)));

        service.timeline(USER);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Map<String, Object>>> events = ArgumentCaptor.forClass(List.class);
        org.mockito.Mockito.verify(ai).careerTimeline(eq(USER), events.capture());
        Map<String, Object> appRow = events.getValue().stream()
                .filter(e -> "application".equals(e.get("kind"))).findFirst().orElseThrow();
        assertThat(appRow).containsEntry("at", "2026-09-01T08:00:00Z");
    }
}
