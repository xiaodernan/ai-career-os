package com.careeros.auth.retention;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.ApiIntegrationTest;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Roadmap 44.3's window, measured against the schema Flyway built.
 *
 * <p>The unit tests pin which cutoff the sweep passes and what the phase counts; this pins the
 * three things only a real database can answer. The chunks go with the row -- the cascade is a
 * line in V1, not a repository anyone calls, so a purge that deleted documents and left their
 * chunks indexed would show up nowhere but here. The predicate that spares a retired row a source
 * still names runs against the real {@code knowledge_sources.document_id} column. And the object
 * behind the purged row's key is asked for after this transaction commits, which is the only
 * moment the retired row has actually stopped naming it: ask earlier and 44.2's own reference
 * check answers "still in use" for the row this purge is deleting.
 *
 * <p>Age is written at insert, never by an update: {@code touch_updated_at} rewrites
 * {@code updated_at} on every UPDATE, so a backdated row would be silently re-aged by the very
 * statement that backdated it -- and the window is measured on that column.
 */
class RetiredEvidencePurgeIT extends ApiIntegrationTest {

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private RetentionSweeper sweeper;

    @Test
    @DisplayName("the window takes the retired row and the chunks indexed from it")
    void thePurgedRowTakesItsChunksWithIt() throws Exception {
        String email = "purge-row-" + UUID.randomUUID() + "@example.com";
        UUID userId = registerUser(email);
        String key = "purge-" + UUID.randomUUID() + "/uploads/resume.pdf";
        storage.store.put(key, "the bytes a delete left".getBytes(StandardCharsets.UTF_8));
        UUID doc = insertDocument(userId, "retired", key, 400);
        insertChunk(doc, userId, 1);
        insertChunk(doc, userId, 2);

        sweeper.sweep(OffsetDateTime.now());

        assertThat(countDocument(doc)).isZero();
        // The backend owns no chunk repository at all -- the ai-service writes them -- so this is
        // the only path that ever removes them, and it removes them because the schema does.
        assertThat(jdbc.queryForObject("select count(*) from document_chunks where document_id = ?",
                Integer.class, doc)).isZero();
        assertThat(storage.store).doesNotContainKey(key);
    }

    @Test
    @DisplayName("a retired row a source still names is left where it is")
    void aSourceNamingARetiredRowKeepsIt() throws Exception {
        String email = "purge-named-" + UUID.randomUUID() + "@example.com";
        UUID userId = registerUser(email);
        String key = "purge-" + UUID.randomUUID() + "/uploads/named.pdf";
        storage.store.put(key, "bytes still reachable".getBytes(StandardCharsets.UTF_8));
        UUID doc = insertDocument(userId, "retired", key, 400);
        insertChunk(doc, userId, 1);
        // The shape the delete path is written not to leave: the copy is retired while a live
        // source row points at it, so the source could still be opened and deleted again.
        jdbc.update("insert into knowledge_sources (id, user_id, kind, title, status, document_id)"
                        + " values (?, ?, ?, ?, ?, ?)", UUID.randomUUID(), userId, "note",
                "a source that survived", "ready", doc);

        sweeper.sweep(OffsetDateTime.now());

        assertThat(countDocument(doc)).isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from document_chunks where document_id = ?",
                Integer.class, doc)).isEqualTo(1);
        assertThat(storage.store).containsKey(key);
    }

    @Test
    @DisplayName("the sweep spares live rows and rows still inside the window")
    void onlyRetiredRowsPastTheWindowGo() throws Exception {
        String email = "purge-kept-" + UUID.randomUUID() + "@example.com";
        UUID userId = registerUser(email);
        UUID liveAged = insertDocument(userId, "ready", null, 400);
        UUID retiredRecent = insertDocument(userId, "retired", null, 10);
        UUID pending = insertDocument(userId, "pending", null, 400);

        sweeper.sweep(OffsetDateTime.now());

        // A row the reader never deleted is not this window's to close, however old it is, and a
        // document still indexing is retryable -- 44.1's terminal status is what marks an end.
        assertThat(countDocument(liveAged)).isEqualTo(1);
        assertThat(countDocument(retiredRecent)).isEqualTo(1);
        assertThat(countDocument(pending)).isEqualTo(1);
    }

    @Test
    @DisplayName("an object another row still names outlives the row this purge deleted")
    void aKeyTwoRowsShareStaysWithTheLiveRow() throws Exception {
        String email = "purge-share-" + UUID.randomUUID() + "@example.com";
        UUID userId = registerUser(email);
        String key = "purge-" + UUID.randomUUID() + "/uploads/shared.pdf";
        storage.store.put(key, "one object, two rows".getBytes(StandardCharsets.UTF_8));
        UUID quotable = insertDocument(userId, "ready", key, 400);
        UUID retired = insertDocument(userId, "retired", key, 400);

        sweeper.sweep(OffsetDateTime.now());

        // The retire is old enough to purge and the purge does take it; the row retrieval can
        // still quote is the reason the bytes stay, which is 44.2's question asked of a row this
        // pass deleted rather than a row the reader deleted.
        assertThat(countDocument(retired)).isZero();
        assertThat(countDocument(quotable)).isEqualTo(1);
        assertThat(storage.store).containsKey(key);
    }

    private UUID registerUser(String email) throws Exception {
        register(email);
        return jdbc.queryForObject("select id from users where email = ?", UUID.class, email);
    }

    private UUID insertDocument(UUID userId, String status, String fileKey, int ageDays) {
        UUID id = UUID.randomUUID();
        OffsetDateTime aged = OffsetDateTime.now().minusDays(ageDays);
        jdbc.update("insert into documents (id, user_id, file_key, media_type, title, content_hash,"
                        + " status, created_at, updated_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                id, userId, fileKey, "application/pdf", "a document", "hash-" + id, status,
                aged, aged);
        return id;
    }

    private void insertChunk(UUID documentId, UUID userId, int ordinal) {
        jdbc.update("insert into document_chunks (document_id, user_id, ordinal, text)"
                        + " values (?, ?, ?, ?)", documentId, userId, ordinal, "chunk " + ordinal);
    }

    private int countDocument(UUID id) {
        Integer rows = jdbc.queryForObject(
                "select count(*) from documents where id = ?", Integer.class, id);
        return rows == null ? 0 : rows;
    }
}
