package com.careeros.interview.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.ApiIntegrationTest;
import com.careeros.auth.repository.UserRepository;
import com.careeros.interview.dto.InterviewDtos.CreateSessionRequest;
import com.careeros.interview.dto.InterviewDtos.SessionItem;
import com.careeros.interview.entity.InterviewSession;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import javax.sql.DataSource;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * Finalizing an interview is one fact told twice: {@code interview_evaluations} carries the scored
 * report, and the session's own row carries the {@code status} and {@code finished_at} that say the
 * report is the end of something. {@code InterviewService.persistFinalization} writes both in that
 * order, and {@code finalize} reached it through a call on itself -- the one route Spring's proxy
 * does not intercept -- so the {@code @Transactional} there armed nothing and each row committed
 * alone.
 *
 * <p>A refusal at the session UPDATE therefore left the reader an evaluation attached to a session
 * still marked {@code active}. That is not a cosmetic mismatch: {@code detail} answers with the
 * evaluation from its own row ({@code InterviewService.detail}) while every screen decides what to
 * show from the status, so the interview reads as finished to the panel that looks up the report and
 * as still running to the list and to the detail page. And {@code answer} checks no status at all,
 * so the same session keeps accepting turns -- each one filed after the report that already closed
 * the conversation, and the report's trajectory no longer matches the turns under it. Both halves
 * are measured here before the fix.
 *
 * <p>The refusal is the database's own but not one of this chain's shipped constraints. Nothing an
 * interview's own answer can carry makes the session UPDATE fail: {@code status} and
 * {@code finished_at} are plain {@code text} and {@code timestamptz} with no check, trigger or
 * unique key beside them, and the evaluation's insert satisfies every constraint it has, because
 * {@code session_id} names a session that already exists and {@code dims}, {@code summary} and
 * {@code trajectory} are {@code jsonb NOT NULL} columns the writer always fills. So the case
 * installs a row-level trigger that refuses this run's session id and treats it as whatever else
 * might refuse that statement at that moment, the way {@link
 * com.careeros.resume.service.ResumeParseAtomicityIT} and {@link
 * com.careeros.knowledge.service.FileIngestAtomicityIT} do; {@link
 * com.careeros.job.service.JobImportAtomicityIT} is the sibling that needs no stand-in. The trigger
 * matches only this run's random id, is dropped after every case, and the IT schema is rebuilt from
 * {@code V1} at the start of each suite run.
 *
 * <p>Two things this file does not measure, and says so rather than implying otherwise. The model
 * call's exclusion from the transaction has no observable here: {@code finalize} writes no row
 * before it, so an implementation that wrapped the call too would pass every case below -- the shape
 * is held by the reading of the code, not by an assertion. And the answering path beside it is not
 * measured here at all: {@code answer}, three lines away in the same class, filed its three rows --
 * the candidate turn, the follow-up, the difficulty step -- with no transaction open anywhere, the
 * blind spot this file's first version named and {@link
 * com.careeros.interview.service.InterviewAnswerAtomicityIT} now holds.
 */
class InterviewFinalizeAtomicityIT extends ApiIntegrationTest {

    @Autowired
    private InterviewService interviews;
    @Autowired
    private InterviewSessionRepository sessionRows;
    @Autowired
    private InterviewEvaluationRepository evaluationRows;
    @Autowired
    private UserRepository users;
    @Autowired
    private DataSource dataSource;

    private final UUID runId = UUID.randomUUID();
    private UUID userId;
    private UUID sessionId;

    @BeforeEach
    void anInterviewThatHasAskedOneQuestion() throws Exception {
        String email = "finalize-atomic-" + runId + "@example.test";
        register(email);
        userId = users.findByEmail(email).orElseThrow().getId();
        SessionItem item = interviews.create(userId, new CreateSessionRequest(null, null, null,
                "ACME GmbH", "Backend Engineer", "technical", Map.of()));
        sessionId = item.id();
        interviews.opening(userId, sessionId);
        assertThat(turnCount())
                .as("a session with no turn cannot be finalized, so the setup has to have asked")
                .isEqualTo(1);
    }

    @AfterEach
    void dropRefusal() throws SQLException {
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON interview_sessions");
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON interview_evaluations");
        execute("DROP FUNCTION IF EXISTS it_refuse_row()");
    }

    private int turnCount() {
        return interviews.detail(userId, sessionId).turns().size();
    }

    private Optional<InterviewSession> session() {
        return sessionRows.findById(sessionId);
    }

    /** The database refuses any row this statement writes for the session under test. */
    private void refuse(String table, String event, String column) throws SQLException {
        execute("CREATE OR REPLACE FUNCTION it_refuse_row() RETURNS trigger LANGUAGE plpgsql AS $$ "
                + "BEGIN "
                + "IF NEW." + column + "::text = '" + sessionId + "' THEN "
                + "RAISE EXCEPTION 'the interview finalize atomicity case refuses this row' "
                + "USING ERRCODE = '23505'; "
                + "END IF; "
                + "RETURN NEW; "
                + "END $$");
        execute("CREATE TRIGGER it_refuse_row BEFORE " + event + " ON " + table
                + " FOR EACH ROW EXECUTE FUNCTION it_refuse_row()");
    }

    private void execute(String sql) throws SQLException {
        try (Connection c = dataSource.getConnection(); Statement st = c.createStatement()) {
            st.execute(sql);
        }
    }

    @Test
    @DisplayName("a successful finalize files the report and closes the session")
    void aSuccessfulFinalizeFilesTheReportAndClosesTheSession() throws SQLException {
        interviews.finalize(userId, sessionId);

        assertThat(evaluationRows.findBySessionId(sessionId))
                .as("the scored report the response carried never reached its row")
                .isPresent();
        InterviewSession closed = session().orElseThrow();
        assertThat(closed.getStatus()).isEqualTo("completed");
        assertThat(closed.getFinishedAt())
                .as("the session says it is completed but not when")
                .isNotNull();
    }

    @Test
    @DisplayName("a refused completion leaves no report attached to a running session")
    void aRefusedCompletionLeavesNoReportAttachedToARunningSession() throws SQLException {
        refuse("interview_sessions", "UPDATE", "id");

        assertThatThrownBy(() -> interviews.finalize(userId, sessionId))
                .isInstanceOf(RuntimeException.class);

        assertThat(evaluationRows.findBySessionId(sessionId))
                .as("the report committed on its own, ahead of the completion that refused")
                .isEmpty();
        InterviewSession stillOpen = session().orElseThrow();
        assertThat(stillOpen.getStatus()).isEqualTo("active");
        assertThat(stillOpen.getFinishedAt()).isNull();
        assertThat(turnCount())
                .as("a session the reader can still answer in gained or lost a turn")
                .isEqualTo(1);
        assertThat(ai.calls)
                .as("the report was asked of the model inside the same unit as its writes")
                .contains("interviewFinalize");
    }

    @Test
    @DisplayName("a refused report row closes nothing")
    void aRefusedReportRowClosesNothing() throws SQLException {
        refuse("interview_evaluations", "INSERT", "session_id");

        assertThatThrownBy(() -> interviews.finalize(userId, sessionId))
                .isInstanceOf(RuntimeException.class);

        assertThat(evaluationRows.findBySessionId(sessionId)).isEmpty();
        InterviewSession stillOpen = session().orElseThrow();
        assertThat(stillOpen.getStatus())
                .as("the session was marked finished around a report that was never filed")
                .isEqualTo("active");
        assertThat(stillOpen.getFinishedAt()).isNull();
    }

    @Test
    @DisplayName("finalizing twice updates the one report row instead of adding a second")
    void finalizingTwiceUpdatesTheOneReportRow() throws SQLException {
        interviews.finalize(userId, sessionId);
        UUID firstId = evaluationRows.findBySessionId(sessionId).orElseThrow().getId();

        interviews.finalize(userId, sessionId);

        assertThat(evaluationRows.findBySessionId(sessionId).orElseThrow().getId())
                .as("the second finalize wrote beside the report it should have replaced")
                .isEqualTo(firstId);
        assertThat(reportRows())
                .as("the unique key on session_id says there was only ever one to replace")
                .isEqualTo(1L);
    }

    /**
     * Counted from the table rather than from {@code findBySessionId}, because the case is claiming
     * there is one row: the read the writer itself uses cannot be the witness for that count.
     */
    private long reportRows() throws SQLException {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(
                     "SELECT count(*) FROM interview_evaluations WHERE session_id = ?")) {
            ps.setObject(1, sessionId);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }
}
