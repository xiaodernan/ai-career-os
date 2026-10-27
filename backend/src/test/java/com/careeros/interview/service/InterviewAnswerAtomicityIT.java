package com.careeros.interview.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.ApiIntegrationTest;
import com.careeros.auth.repository.UserRepository;
import com.careeros.interview.dto.InterviewDtos.AnswerResponse;
import com.careeros.interview.dto.InterviewDtos.CreateSessionRequest;
import com.careeros.interview.dto.InterviewDtos.SessionItem;
import com.careeros.interview.entity.InterviewSession;
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
 * One answer is three rows filed in sequence: the candidate's turn ({@code persistTurnAnswer}),
 * the follow-up question the reply orders ({@code persistTurn}), and the difficulty step on the
 * session's own row. No writer among them holds two -- each helper files exactly one -- so the
 * census, which counted writes per writer, never charged the exchange even though it can file
 * three rows between two commits. {@link InterviewFinalizeAtomicityIT} named the blind spot when
 * it closed the finalize half; this file holds the answer half, which is the shape the gate now
 * reads as a spread.
 *
 * <p>Filed apart, a refusal partway leaves a transcript that lies by halves. The candidate's turn
 * sits under the session as asked-and-answered while the follow-up it earned never arrives, and
 * the difficulty the evaluation computed never moves the session; the detail page renders the
 * half exchange as a finished beat. A refusal at the session's own UPDATE is worse: both turns
 * committed beside a difficulty step that never landed, so the session grew a round it cannot
 * account for.
 *
 * <p>The refusal is the database's own but not one of this chain's shipped constraints. Nothing
 * an answer can carry refuses these rows: {@code content} is plain {@code text}, {@code
 * difficulty} is a bare float, and the {@code (session_id, seq)} pair the turns' unique key
 * guards is satisfied by construction -- the writer computes each seq from the rows it just
 * read. So the case installs a row-level trigger, the way {@link InterviewFinalizeAtomicityIT}
 * does, keyed to this run's session id and to the role whose INSERT is under test, dropped after
 * every case.
 *
 * <p>The first refusal case is the aim, not a discriminator: the candidate row is the first write
 * the exchange files, so refusing it is green before and after the fix -- what it proves is that
 * the trigger aims at the row the exchange files first, which the two cases after it lean on. The
 * model call stays outside the transaction, as does every read the exchange opens with, so no
 * pooled connection waits on ai-service; the cases that refuse a later row measure what the
 * writes alone left behind.
 */
class InterviewAnswerAtomicityIT extends ApiIntegrationTest {

    @Autowired
    private InterviewService interviews;
    @Autowired
    private InterviewSessionRepository sessionRows;
    @Autowired
    private UserRepository users;
    @Autowired
    private DataSource dataSource;

    private final UUID runId = UUID.randomUUID();
    private UUID userId;
    private UUID sessionId;

    @BeforeEach
    void anInterviewThatHasAskedOneQuestion() throws Exception {
        String email = "answer-atomic-" + runId + "@example.test";
        register(email);
        userId = users.findByEmail(email).orElseThrow().getId();
        SessionItem item = interviews.create(userId, new CreateSessionRequest(null, null, null,
                "ACME GmbH", "Backend Engineer", "technical", Map.of()));
        sessionId = item.id();
        interviews.opening(userId, sessionId);
        assertThat(turnRows())
                .as("an exchange with no question behind it cannot take an answer")
                .isEqualTo(1L);
    }

    @AfterEach
    void dropRefusal() throws SQLException {
        execute("DROP TRIGGER IF EXISTS it_refuse_answer_row ON interview_turns");
        execute("DROP TRIGGER IF EXISTS it_refuse_answer_row ON interview_sessions");
        execute("DROP FUNCTION IF EXISTS it_refuse_answer_row()");
    }

    /** The database refuses any row this statement writes for the predicate's slice. */
    private void refuse(String table, String event, String predicate) throws SQLException {
        execute("CREATE OR REPLACE FUNCTION it_refuse_answer_row() RETURNS trigger "
                + "LANGUAGE plpgsql AS $$ "
                + "BEGIN "
                + "IF " + predicate + " THEN "
                + "RAISE EXCEPTION 'the interview answer atomicity case refuses this row' "
                + "USING ERRCODE = '23505'; "
                + "END IF; "
                + "RETURN NEW; "
                + "END $$");
        execute("CREATE TRIGGER it_refuse_answer_row BEFORE " + event + " ON " + table
                + " FOR EACH ROW EXECUTE FUNCTION it_refuse_answer_row()");
    }

    private void execute(String sql) throws SQLException {
        try (Connection c = dataSource.getConnection(); Statement st = c.createStatement()) {
            st.execute(sql);
        }
    }

    /**
     * Counted from the table rather than from {@code detail}, because the case is claiming how
     * many rows the exchange filed: the read the writer itself uses cannot be the witness for
     * that count.
     */
    private long turnRows() throws SQLException {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(
                     "SELECT count(*) FROM interview_turns WHERE session_id = ?")) {
            ps.setObject(1, sessionId);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getLong(1);
            }
        }
    }

    private Optional<InterviewSession> session() {
        return sessionRows.findById(sessionId);
    }

    @Test
    @DisplayName("a successful answer files the candidate's turn, the follow-up and the difficulty step")
    void aSuccessfulAnswerFilesTheWholeExchange() throws SQLException {
        AnswerResponse reply = interviews.answer(userId, sessionId,
                "We sharded by tenant and put reads on replicas.");

        assertThat(turnRows())
                .as("the question the setup asked, the answer and the follow-up it earned")
                .isEqualTo(3L);
        assertThat(reply.candidateTurn().seq()).isEqualTo(2);
        assertThat(reply.candidateTurn().role()).isEqualTo("candidate");
        assertThat(reply.followup())
                .as("the follow-up the reply ordered is a row of its own")
                .isNotNull();
        assertThat(reply.followup().seq()).isEqualTo(3);
        assertThat(reply.followup().role()).isEqualTo("interviewer");
        assertThat(reply.followup().content())
                .as("the follow-up row carries the model's question")
                .isEqualTo("How did you handle data consistency during scaling?");
        assertThat(reply.session().difficulty())
                .as("the difficulty the evaluation computed moved the session")
                .isEqualTo(0.65f);
        assertThat(ai.calls).contains("interviewAnswer");
    }

    @Test
    @DisplayName("a refusal at the exchange's first row files nothing after it")
    void aRefusalAtTheFirstRowFilesNothing() throws SQLException {
        refuse("interview_turns", "INSERT",
                "NEW.session_id::text = '" + sessionId + "' AND NEW.role = 'candidate'");

        assertThatThrownBy(() -> interviews.answer(userId, sessionId, "We sharded by tenant."))
                .isInstanceOf(RuntimeException.class);

        assertThat(turnRows())
                .as("the exchange's rows when its first row is the one refused")
                .isEqualTo(1L);
        assertThat(session().orElseThrow().getDifficulty())
                .as("the difficulty step follows the rows it grades")
                .isEqualTo(0.5f);
        assertThat(ai.calls)
                .as("the model ran before the write that refused")
                .contains("interviewAnswer");
    }

    @Test
    @DisplayName("a refused follow-up leaves no candidate turn behind")
    void aRefusedFollowupLeavesNoCandidateTurnBehind() throws SQLException {
        refuse("interview_turns", "INSERT",
                "NEW.session_id::text = '" + sessionId + "' AND NEW.role = 'interviewer'");

        assertThatThrownBy(() -> interviews.answer(userId, sessionId, "We sharded by tenant."))
                .isInstanceOf(RuntimeException.class);

        assertThat(turnRows())
                .as("the candidate's turn stayed behind the follow-up that refused")
                .isEqualTo(1L);
        assertThat(session().orElseThrow().getDifficulty())
                .as("the difficulty step follows the rows it grades")
                .isEqualTo(0.5f);
    }

    @Test
    @DisplayName("a refused difficulty step leaves neither turn behind")
    void aRefusedDifficultyStepLeavesNoTurnBehind() throws SQLException {
        refuse("interview_sessions", "UPDATE", "NEW.id::text = '" + sessionId + "'");

        assertThatThrownBy(() -> interviews.answer(userId, sessionId, "We sharded by tenant."))
                .isInstanceOf(RuntimeException.class);

        assertThat(turnRows())
                .as("the candidate's turn and the follow-up it earned stayed behind the step that refused")
                .isEqualTo(1L);
        assertThat(session().orElseThrow().getDifficulty())
                .as("the difficulty step the refusal landed on")
                .isEqualTo(0.5f);
    }
}
