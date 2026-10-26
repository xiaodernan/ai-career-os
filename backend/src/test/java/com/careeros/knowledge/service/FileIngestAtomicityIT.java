package com.careeros.knowledge.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.ApiIntegrationTest;
import com.careeros.auth.repository.UserRepository;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.knowledge.service.FileIngestService.Persisted;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.UUID;
import javax.sql.DataSource;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * An upload's two rows only mean something together: {@code knowledge_sources} carries the title the
 * list shows and the status the badge reads, {@code documents} carries the file the chunks are cut
 * from, and each row names the other. {@code FileIngestService.persistRows} writes three statements
 * to build that pair -- source, document, then the source's back-pointer -- and both of the entry
 * points that reach it did so through a call on itself, which is the one route Spring's proxy does
 * not intercept. The {@code @Transactional} on {@code persistRows} therefore armed nothing and each
 * of the three statements committed alone.
 *
 * <p>So a refusal at the document INSERT left the reader a source row titled like a finished upload
 * -- status {@code ingesting}, {@code document_id} null -- which is an entry that can never become
 * ready, can never be cited, and never stops saying {@code ingesting}. Refusing the linking UPDATE
 * instead left the document filed and its source still pointing at nothing. Both halves are measured
 * here before the fix.
 *
 * <p>The refusal is the database's own but not one of this chain's shipped constraints: every column
 * of both tables is {@code text}, no unique key covers them, and {@code fk_ks_document} is
 * {@code DEFERRABLE INITIALLY DEFERRED} -- so nothing an upload's own bytes can carry makes
 * {@code persistRows} refuse partway. The case therefore installs a row-level trigger that refuses a
 * sentinel title and treats it as whatever else might refuse that statement at that moment, the way
 * {@link com.careeros.resume.service.ResumeParseAtomicityIT} does; {@link
 * com.careeros.job.service.JobImportAtomicityIT} is the sibling that needs no stand-in. The trigger
 * matches only the title carrying this run's random id, is dropped after every case, and the IT
 * schema is rebuilt from {@code V1} at the start of each suite run.
 *
 * <p>{@code uploadAndIngest} is graded here too although no caller reaches it -- {@code
 * ai-service/tests/test_file_key_composers.py} names it as the one folder-taking entry point with no
 * in-tree caller, and {@code KnowledgeService.uploadDocument} is its live replacement -- because the
 * census charges the shape of the call, not its reachability. It carries a second self-invocation
 * this unit leaves alone: its failure path calls {@code markFailed}, which writes by dirty checking
 * rather than by a {@code save} call, so the census never sees it and no case here measures it.
 */
class FileIngestAtomicityIT extends ApiIntegrationTest {

    @Autowired
    private FileIngestService ingest;
    @Autowired
    private KnowledgeSourceRepository sourceRows;
    @Autowired
    private DocumentRepository documentRows;
    @Autowired
    private UserRepository users;
    @Autowired
    private DataSource dataSource;

    private final UUID runId = UUID.randomUUID();
    private UUID userId;

    @BeforeEach
    void anAccount() throws Exception {
        String email = "ingest-atomic-" + runId + "@example.test";
        register(email);
        userId = users.findByEmail(email).orElseThrow().getId();
    }

    @AfterEach
    void dropRefusal() throws SQLException {
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON documents");
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON knowledge_sources");
        execute("DROP FUNCTION IF EXISTS it_refuse_row()");
    }

    /** Text bytes are the one type {@code FileValidator} accepts without a magic header. */
    private byte[] content(String stem) {
        return ("Kubernetes guide " + stem).getBytes(StandardCharsets.UTF_8);
    }

    private int count(String table, String title) throws SQLException {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(
                     "SELECT count(*) FROM " + table + " WHERE title = ?")) {
            ps.setString(1, title);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                return rs.getInt(1);
            }
        }
    }

    private void execute(String sql) throws SQLException {
        try (Connection c = dataSource.getConnection(); Statement st = c.createStatement()) {
            st.execute(sql);
        }
    }

    /** The database refuses any row titled {@code value} that this statement tries to write. */
    private void refuse(String table, String event, String value) throws SQLException {
        execute("CREATE OR REPLACE FUNCTION it_refuse_row() RETURNS trigger LANGUAGE plpgsql AS $$ "
                + "BEGIN "
                + "IF NEW.title = '" + value + "' THEN "
                + "RAISE EXCEPTION 'the file ingest atomicity case refuses this row' "
                + "USING ERRCODE = '23505'; "
                + "END IF; "
                + "RETURN NEW; "
                + "END $$");
        execute("CREATE TRIGGER it_refuse_row BEFORE " + event + " ON " + table
                + " FOR EACH ROW EXECUTE FUNCTION it_refuse_row()");
    }

    @Test
    @DisplayName("a successful persist files the pair with each row naming the other")
    void persistRowsOnlyFilesTheSourceAndItsDocumentLinked() throws SQLException {
        String title = "Linked Upload " + runId;

        Persisted persisted = ingest.persistRowsOnly(userId, content(title), title, "note", "knowledge");

        KnowledgeSource source = sourceRows.findById(persisted.sourceId()).orElseThrow();
        Document document = documentRows.findById(persisted.documentId()).orElseThrow();
        assertThat(source.getDocumentId())
                .as("the source row does not point at the document it just gained")
                .isEqualTo(persisted.documentId());
        assertThat(document.getSourceId())
                .as("the document row does not point back at its source")
                .isEqualTo(persisted.sourceId());
        assertThat(count("knowledge_sources", title)).isEqualTo(1);
        assertThat(count("documents", title)).isEqualTo(1);
    }

    @Test
    @DisplayName("a refused document row leaves no source titled like a finished upload")
    void aRefusedDocumentRowLeavesNoOrphanSource() throws SQLException {
        String title = "Refused Document " + runId;
        refuse("documents", "INSERT", title);

        assertThatThrownBy(() -> ingest.persistRowsOnly(userId, content(title), title, "note", "knowledge"))
                .isInstanceOf(RuntimeException.class);

        assertThat(count("knowledge_sources", title))
                .as("the source committed on its own, ahead of the document that refused")
                .isZero();
        assertThat(count("documents", title)).isZero();
    }

    @Test
    @DisplayName("a refused link rolls back the document row that already succeeded")
    void aRefusedLinkRollsBackTheDocumentAlreadyFiled() throws SQLException {
        String title = "Refused Link " + runId;
        refuse("knowledge_sources", "UPDATE", title);

        assertThatThrownBy(() -> ingest.persistRowsOnly(userId, content(title), title, "note", "knowledge"))
                .isInstanceOf(RuntimeException.class);

        assertThat(count("documents", title))
                .as("the document stayed behind the back-pointer that could not be written")
                .isZero();
        assertThat(count("knowledge_sources", title))
                .as("the source row stayed with document_id null")
                .isZero();
    }

    @Test
    @DisplayName("uploadAndIngest files its pair before it hands the document to ai-service")
    void uploadAndIngestFilesThePairTheIngestTriggerPointsAt() throws SQLException {
        String stem = "Triggered Upload " + runId;

        Persisted persisted = ingest.uploadAndIngest(userId, content(stem), stem + ".txt",
                "note", "knowledge", null);

        assertThat(ai.calls).contains("ingestDocument");
        assertThat(count("knowledge_sources", stem)).isEqualTo(1);
        assertThat(count("documents", stem)).isEqualTo(1);
        assertThat(sourceRows.findById(persisted.sourceId()).orElseThrow().getDocumentId())
                .isEqualTo(persisted.documentId());
    }

    @Test
    @DisplayName("a refused document row leaves uploadAndIngest with nothing to trigger")
    void aRefusedUploadAndIngestDocumentRowFilesNothing() throws SQLException {
        String stem = "Refused Trigger " + runId;
        refuse("documents", "INSERT", stem);

        assertThatThrownBy(() -> ingest.uploadAndIngest(userId, content(stem), stem + ".txt",
                "note", "knowledge", null))
                .isInstanceOf(RuntimeException.class);

        assertThat(count("knowledge_sources", stem))
                .as("the source of an upload that never reached the model was left behind")
                .isZero();
        assertThat(ai.calls)
                .as("the ingest trigger ran against a document row that was never filed")
                .doesNotContain("ingestDocument");
    }
}
