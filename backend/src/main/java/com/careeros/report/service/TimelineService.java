package com.careeros.report.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.entity.Application;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.common.Paging;
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
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * One timeline over the whole loop (Epic 81).
 *
 * <p>The product writes six kinds of dated rows about the reader's search --
 * applications, notes, contacts, resume versions, matches and interview
 * rehearsals -- and each is scored to zero readers per screen: the reader has no
 * single place to scroll and see "what happened, in order". This bridge reads the
 * caller's own tables, maps each row to the engine's own field names, hands the
 * whole set to the ai-service's pure deterministic merge, and forwards its
 * answer. Neither the bridge nor the engine invents a date, a kind or a summary
 * the rows do not carry.
 *
 * <p>The rows are capped per source before they travel: the engine is a pure
 * partition over what it is given, and an unbounded read would make one slow
 * account slow down every reader's timeline. The cap keeps the timeline useful
 * (the most recent of each kind, 50 rows each) instead of unbounded.
 */
@Service
public class TimelineService {

    private static final int PER_SOURCE_CAP = 50;

    private final AiServiceClient ai;
    private final ApplicationRepository applications;
    private final UserNoteRepository notes;
    private final ContactRepository contacts;
    private final ResumeVersionRepository resumeVersions;
    private final JobMatchRepository matches;
    private final InterviewSessionRepository interviews;

    public TimelineService(AiServiceClient ai, ApplicationRepository applications,
                           UserNoteRepository notes, ContactRepository contacts,
                           ResumeVersionRepository resumeVersions, JobMatchRepository matches,
                           InterviewSessionRepository interviews) {
        this.ai = ai;
        this.applications = applications;
        this.notes = notes;
        this.contacts = contacts;
        this.resumeVersions = resumeVersions;
        this.matches = matches;
        this.interviews = interviews;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> timeline(UUID userId) {
        List<Map<String, Object>> events = new ArrayList<>();
        applications.findByUserIdOrderByUpdatedAtDescIdAsc(userId, Paging.first(PER_SOURCE_CAP)).getContent()
                .forEach(a -> events.add(applicationRow(a)));
        notes.findByUserIdOrderByUpdatedAtDescIdAsc(userId, Paging.first(PER_SOURCE_CAP)).getContent()
                .forEach(n -> events.add(noteRow(n)));
        contacts.findByUserIdOrderByUpdatedAtDescIdAsc(userId, Paging.first(PER_SOURCE_CAP)).getContent()
                .forEach(c -> events.add(contactRow(c)));
        resumeVersions.findByUserIdOrderByCreatedAtDescIdAsc(userId, Paging.first(PER_SOURCE_CAP))
                .getContent().forEach(v -> events.add(resumeVersionRow(v)));
        matches.findByUserIdOrderByCreatedAtDescIdAsc(userId, Paging.first(PER_SOURCE_CAP))
                .getContent().forEach(m -> events.add(matchRow(m)));
        interviews.findPage(userId, null, "", Paging.first(PER_SOURCE_CAP)).getContent()
                .forEach(s -> events.add(interviewRow(s)));
        return ai.careerTimeline(userId, events);
    }

    private Map<String, Object> applicationRow(Application a) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("at", iso(a.getAppliedAt() != null ? a.getAppliedAt() : a.getCreatedAt()));
        row.put("kind", "application");
        row.put("title", a.getCompanyName() == null || a.getCompanyName().isBlank()
                ? a.getTitle() : a.getTitle() + " · " + a.getCompanyName());
        row.put("refId", String.valueOf(a.getId()));
        row.put("summary", "status: " + a.getStatus());
        return row;
    }

    private Map<String, Object> noteRow(UserNote n) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("at", iso(n.getCreatedAt()));
        row.put("kind", "note");
        String title = n.getTitle();
        row.put("title", title == null || title.isBlank() ? "Note" : title);
        row.put("refId", String.valueOf(n.getId()));
        List<String> tags = n.getTags();
        row.put("summary", tags.isEmpty() ? "note" : "#" + String.join(" #", tags));
        return row;
    }

    private Map<String, Object> contactRow(Contact c) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("at", iso(c.getCreatedAt()));
        row.put("kind", "contact");
        row.put("title", "Added " + c.getName());
        row.put("refId", String.valueOf(c.getId()));
        String relation = c.getRelation();
        row.put("summary", relation == null || relation.isBlank() ? "contact" : relation);
        return row;
    }

    private Map<String, Object> resumeVersionRow(ResumeVersion v) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("at", iso(v.getCreatedAt()));
        row.put("kind", "resume_version");
        String label = v.getLabel();
        row.put("title", "Resume version" + (label == null || label.isBlank() ? "" : " · " + label));
        row.put("refId", String.valueOf(v.getId()));
        row.put("summary", "kind: " + v.getKind());
        return row;
    }

    private Map<String, Object> matchRow(JobMatch m) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("at", iso(m.getCreatedAt()));
        row.put("kind", "match");
        row.put("title", "Match");
        row.put("refId", String.valueOf(m.getId()));
        row.put("summary", "overall " + m.getOverall());
        return row;
    }

    private Map<String, Object> interviewRow(InterviewSession s) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("at", iso(s.getStartedAt()));
        row.put("kind", "interview");
        String position = s.getPositionTitle();
        row.put("title", position == null || position.isBlank() ? "Interview rehearsal" : position);
        row.put("refId", String.valueOf(s.getId()));
        row.put("summary", "mode " + s.getMode() + ", " + s.getStatus());
        return row;
    }

    private static String iso(OffsetDateTime value) {
        return value == null ? "" : value.toInstant().toString();
    }
}
