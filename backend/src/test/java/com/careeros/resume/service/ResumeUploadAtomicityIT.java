package com.careeros.resume.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.ApiIntegrationTest;
import com.careeros.auth.repository.UserRepository;
import com.careeros.knowledge.entity.Document;
import com.careeros.knowledge.entity.KnowledgeSource;
import com.careeros.knowledge.repository.DocumentRepository;
import com.careeros.knowledge.repository.KnowledgeSourceRepository;
import com.careeros.resume.dto.ResumeDtos.UploadResumeResponse;
import com.careeros.resume.entity.Resume;
import com.careeros.resume.repository.ResumeRepository;
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
import org.springframework.mock.web.MockMultipartFile;

/**
 * An upload is one unit filed across two beans: {@code FileIngestService.persistRows} writes the
 * knowledge source and its document, and {@code ResumeService.persistUpload} writes the resume
 * row, the v1 version (through {@code newVersion}), the current-version pointer and the source's
 * {@code ref_id} back-link. {@code ResumeService.upload} opened no transaction and reached its
 * {@code @Transactional} writer through a call on itself -- the one route Spring's proxy does not
 * intercept -- so the four resume-side writes ran with no transaction at all while
 * {@code persistRows} committed in one of its own. Three consequences, each measured here before
 * the fix:
 *
 * <p>A refusal at the resume INSERT left the knowledge pair behind: a source row titled like a
 * finished upload pointing at a document nobody's resume ever owned. A refusal at the version
 * INSERT left a resume row with no version under it and a null current-version pointer. A refusal
 * at the {@code ref_id} back-link left the resume, its version and the whole knowledge pair --
 * everything filed before the link that failed.
 *
 * <p>The refusal in the last three cases is the database's own but not one of this chain's shipped
 * constraints: every column the chain fills comes from generated ids or the file itself, and
 * {@code fk_ks_document} is {@code DEFERRABLE INITIALLY DEFERRED} -- so nothing an upload's own
 * bytes can carry makes {@code persistUpload} refuse partway. The case therefore installs a
 * row-level trigger that refuses any row carrying this case's user id and treats it as whatever
 * else might refuse that statement at that moment, the way {@code FileIngestAtomicityIT} does;
 * {@code JobImportAtomicityIT} is the sibling that needs no stand-in. The trigger on the
 * knowledge-source UPDATE fires only when {@code ref_id} becomes non-null, so
 * {@code persistRows}' own back-pointer UPDATE passes untouched. The trigger is dropped after
 * every case, and the IT schema is rebuilt from {@code V1} at the start of each suite run.
 *
 * <p>Two shapes this unit leaves alone. The stored file is written before any row is: a
 * transaction can roll the rows back but not the bytes, so a refused upload still leaves its
 * object in storage -- the IT runs on in-memory storage and asserts nothing about it. And the
 * failure path of {@code upload} calls {@code markUploadFailed}, which writes by dirty checking
 * rather than by a {@code save} call, so the census never sees it and no case here measures it --
 * the same second self-invocation {@code FileIngestAtomicityIT} discloses for
 * {@code uploadAndIngest}.
 */
class ResumeUploadAtomicityIT extends ApiIntegrationTest {

    @Autowired
    private ResumeService resumes;
    @Autowired
    private ResumeRepository resumeRows;
    @Autowired
    private DocumentRepository documentRows;
    @Autowired
    private KnowledgeSourceRepository sourceRows;
    @Autowired
    private UserRepository users;
    @Autowired
    private DataSource dataSource;

    private final UUID runId = UUID.randomUUID();
    private UUID userId;

    @BeforeEach
    void anAccount() throws Exception {
        String email = "upload-atomic-" + runId + "@example.test";
        register(email);
        userId = users.findByEmail(email).orElseThrow().getId();
    }

    @AfterEach
    void dropRefusal() throws SQLException {
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON resumes");
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON resume_versions");
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON knowledge_sources");
        execute("DROP FUNCTION IF EXISTS it_refuse_row()");
    }

    private MockMultipartFile file(String title) {
        return new MockMultipartFile("file", title + ".txt", "text/plain",
                ("Kubernetes guide " + title).getBytes(StandardCharsets.UTF_8));
    }

    private int count(String table) throws SQLException {
        try (Connection c = dataSource.getConnection();
             PreparedStatement ps = c.prepareStatement(
                     "SELECT count(*) FROM " + table + " WHERE user_id = ?")) {
            ps.setObject(1, userId);
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

    /** Refuses every row of {@code table} this case's user writes, whatever the statement is. */
    private void refuse(String table, String event) throws SQLException {
        // The knowledge-source back-pointer UPDATE persistRows itself makes keeps ref_id null, so
        // keying the refusal on ref_id arriving aims it at the one UPDATE this chain ends with.
        String keyed = table.equals("knowledge_sources")
                ? "NEW.user_id::text = '" + userId + "' AND NEW.ref_id IS NOT NULL"
                : "NEW.user_id::text = '" + userId + "'";
        execute("CREATE OR REPLACE FUNCTION it_refuse_row() RETURNS trigger LANGUAGE plpgsql AS $$ "
                + "BEGIN "
                + "IF " + keyed + " THEN "
                + "RAISE EXCEPTION 'the resume upload atomicity case refuses this row' "
                + "USING ERRCODE = '23505'; "
                + "END IF; "
                + "RETURN NEW; "
                + "END $$");
        execute("CREATE TRIGGER it_refuse_row BEFORE " + event + " ON " + table
                + " FOR EACH ROW EXECUTE FUNCTION it_refuse_row()");
    }

    @Test
    @DisplayName("a successful upload files every row the chain names, each pointing at the next")
    void aSuccessfulUploadFilesEveryRowTheChainNames() throws SQLException {
        String title = "Linked Upload " + runId;

        UploadResumeResponse uploaded = resumes.upload(userId, file(title));

        assertThat(ai.calls).contains("ingestDocument");
        Resume resume = resumeRows.findById(uploaded.resumeId()).orElseThrow();
        assertThat(resume.getStatus()).isEqualTo("uploaded");
        assertThat(resume.getCurrentVersionId())
                .as("the resume does not point at the version filed beside it")
                .isEqualTo(uploaded.versionId());
        KnowledgeSource source = sourceRows.findById(uploaded.sourceId()).orElseThrow();
        assertThat(source.getRefId())
                .as("the knowledge source does not point back at the resume it was filed for")
                .isEqualTo(uploaded.resumeId());
        assertThat(source.getDocumentId())
                .as("the knowledge source does not point at the document its file was cut from")
                .isEqualTo(uploaded.documentId());
        Document document = documentRows.findById(uploaded.documentId()).orElseThrow();
        assertThat(document.getSourceId()).isEqualTo(uploaded.sourceId());
    }

    @Test
    @DisplayName("a refused resume row leaves no knowledge entry titled like a finished upload")
    void aRefusedResumeRowLeavesNoKnowledgeEntryBehind() throws SQLException {
        String title = "Refused Resume " + runId;
        refuse("resumes", "INSERT");

        assertThatThrownBy(() -> resumes.upload(userId, file(title)))
                .isInstanceOf(RuntimeException.class);

        assertThat(ai.calls)
                .as("the ingest trigger ran against a resume that never filed")
                .doesNotContain("ingestDocument");
        assertThat(count("resumes")).isZero();
        assertThat(count("resume_versions")).isZero();
        assertThat(count("knowledge_sources"))
                .as("the source of an upload whose resume was refused stayed behind")
                .isZero();
        assertThat(count("documents"))
                .as("the document of an upload whose resume was refused stayed behind")
                .isZero();
    }

    @Test
    @DisplayName("a refused version row leaves no resume row under it")
    void aRefusedVersionRowLeavesNoResumeBehind() throws SQLException {
        String title = "Refused Version " + runId;
        refuse("resume_versions", "INSERT");

        assertThatThrownBy(() -> resumes.upload(userId, file(title)))
                .isInstanceOf(RuntimeException.class);

        assertThat(ai.calls)
                .as("the ingest trigger ran against a resume that never filed")
                .doesNotContain("ingestDocument");
        assertThat(count("resumes"))
                .as("the resume row survived the version that refused beside it")
                .isZero();
        assertThat(count("resume_versions")).isZero();
        assertThat(count("knowledge_sources"))
                .as("the source of an upload whose version was refused stayed behind")
                .isZero();
        assertThat(count("documents"))
                .as("the document of an upload whose version was refused stayed behind")
                .isZero();
    }

    @Test
    @DisplayName("a refused back-link rolls back the resume, its version and the knowledge pair")
    void aRefusedBackLinkRollsBackEverythingFiledBeforeIt() throws SQLException {
        String title = "Refused Back-link " + runId;
        refuse("knowledge_sources", "UPDATE");

        assertThatThrownBy(() -> resumes.upload(userId, file(title)))
                .isInstanceOf(RuntimeException.class);

        assertThat(ai.calls)
                .as("the ingest trigger ran against a resume that never filed")
                .doesNotContain("ingestDocument");
        assertThat(count("resumes"))
                .as("the resume row survived the back-link that refused it")
                .isZero();
        assertThat(count("resume_versions"))
                .as("the version row survived the back-link that refused its resume")
                .isZero();
        assertThat(count("knowledge_sources"))
                .as("the unlinked source row survived its own refusal")
                .isZero();
        assertThat(count("documents"))
                .as("the document row survived the back-link that refused its source")
                .isZero();
    }
}
