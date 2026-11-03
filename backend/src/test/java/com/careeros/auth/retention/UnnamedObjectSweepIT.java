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
 * Roadmap 48.2's judgement, measured against the schema Flyway built.
 *
 * <p>The unit tests pin the order of the two reads and what the pass does with a verdict; four
 * things only a real database can answer live here. The document read has no status filter, and
 * "no status filter" is a property of SQL over a column rather than of a mock that returns what
 * it is told -- a future edit that reuses 44.2's retired-excluding predicate would pass every
 * stub and start reclaiming bytes an audit record still names. The resume read runs against the
 * real {@code resumes.source_file_key} column, which is nullable, so a typo in the field name
 * fails at boot here and nowhere else. The two reads are not scoped to an account, because the
 * bucket is not partitioned by one: a key another reader's row holds is a claim on these bytes.
 * And the window is measured on the date the store itself gave the object, which is the double's
 * own map rather than a column.
 *
 * <p>Objects are aged by writing the double's {@code storedAt} entry, never by touching a row: the
 * sweep asks the store when the bytes landed, and 48.1 made that answer the store's to give.
 */
class UnnamedObjectSweepIT extends ApiIntegrationTest {

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private RetentionSweeper sweeper;

    @Test
    @DisplayName("the orphan goes, the young object and the dated-at-the-edge object stay")
    void onlyAnOrphanPastTheWindowIsReclaimed() throws Exception {
        String orphan = seed("orphan", 30);
        String young = seed("young", 1);
        // The boundary is judged toward keeping: six days old is inside a seven-day window, and
        // the object that would go on an off-by-one is the one a reader is still waiting for.
        String justInside = seed("inside", 6);

        sweeper.sweep(OffsetDateTime.now());

        assertThat(storage.store).doesNotContainKey(orphan);
        assertThat(storage.store).containsKeys(young, justInside);
    }

    @Test
    @DisplayName("a retired document row still names its key to the bucket")
    void aRetiredRowIsAnOwnerEvenThoughItIsNotQuotable() throws Exception {
        UUID userId = registerUser("bucket-retired");
        String key = seed("retired-key", 30);
        insertDocument(userId, "retired", key);

        sweeper.sweep(OffsetDateTime.now());

        // 44.2 excludes retired rows because an audit record is no reason to hold bytes a reader
        // deleted; 48.2 includes them because a row that exists is still pointing. The purge is
        // what releases the object, and it does that through the reclaimer, not by accident --
        // which is why this row is aged a month and not the 180 days that would take it away.
        assertThat(storage.store).containsKey(key);
    }

    @Test
    @DisplayName("a resume that serves its own upload keeps the bytes")
    void aResumeNamingItsUploadIsAnOwner() throws Exception {
        UUID userId = registerUser("bucket-resume");
        String key = seed("resume-key", 30);
        jdbc.update("insert into resumes (id, user_id, title, source_file_key, status)"
                + " values (?, ?, ?, ?, ?)", UUID.randomUUID(), userId, "a resume", key, "parsed");

        sweeper.sweep(OffsetDateTime.now());

        // The detail page hands back the bytes this key names, so a sweep that read only the
        // document table would delete a file a reader can still open.
        assertThat(storage.store).containsKey(key);
    }

    @Test
    @DisplayName("another account's row is still an owner of the object")
    void theOwnersAreCensusedAcrossTheWholeInstall() throws Exception {
        UUID owner = registerUser("bucket-owner");
        String key = seed("shared-key", 30);
        insertDocument(owner, "ready", key);

        sweeper.sweep(OffsetDateTime.now());

        // Nothing in this pass is scoped by user: the bucket is one namespace, and the claim on an
        // object is a row anywhere in it. Account erasure is the delete that reaches across.
        assertThat(storage.store).containsKey(key);
    }

    @Test
    @DisplayName("an object whose row was never written is reclaimed for the whole install")
    void anOrphanFromAFailedIngestGoesTheNextNight() throws Exception {
        // The shape the epic exists for: the bytes landed, the row did not, and no path written
        // before 48.2 can see the difference -- every other delete starts from a row.
        String orphan = seed("never-named", 8);
        UUID userId = registerUser("bucket-orphan");
        insertDocument(userId, "ready", seed("named-doc", 8));

        sweeper.sweep(OffsetDateTime.now());

        assertThat(storage.store).doesNotContainKey(orphan);
        assertThat(countDocuments(userId)).isEqualTo(1);
    }

    private String seed(String label, int ageDays) {
        String key = "bucket-" + label + "-" + UUID.randomUUID() + "/uploads/x.bin";
        storage.store.put(key, "the bytes a sweep judges".getBytes(StandardCharsets.UTF_8));
        storage.storedAt.put(key, OffsetDateTime.now().minusDays(ageDays));
        return key;
    }

    private UUID registerUser(String prefix) throws Exception {
        String email = prefix + "-" + UUID.randomUUID() + "@example.com";
        register(email);
        return jdbc.queryForObject("select id from users where email = ?", UUID.class, email);
    }

    private void insertDocument(UUID userId, String status, String fileKey) {
        OffsetDateTime aged = OffsetDateTime.now().minusDays(30);
        jdbc.update("insert into documents (id, user_id, file_key, media_type, title, content_hash,"
                        + " status, created_at, updated_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                UUID.randomUUID(), userId, fileKey, "application/pdf", "a document",
                "hash-" + UUID.randomUUID(), status, aged, aged);
    }

    private int countDocuments(UUID userId) {
        Integer rows = jdbc.queryForObject(
                "select count(*) from documents where user_id = ?", Integer.class, userId);
        return rows == null ? 0 : rows;
    }
}
