package com.careeros.storage;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.config.AppProperties;
import com.careeros.storage.StorageService.StoredObject;
import com.careeros.support.InMemoryStorageConfig.InMemoryStorageService;
import java.io.IOException;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * The listing a reclaim has to trust (48.1). A sweep decides whether bytes are garbage by subtracting
 * every key a row names from every key the bucket shows, so the one thing the port may not do is
 * answer less than the whole bucket: a short list reads as "nothing else is here" and the objects past
 * what it reached are deleted as orphans. These cases hold the double to that promise -- everything it
 * holds, dated, and dated honestly -- and hold the real store to the refusal half of it.
 */
class StorageListingTest {

    private static final String KNOWLEDGE_KEY = "11111111-1111-4111-8111-111111111111/knowledge/blob.pdf";
    private static final String RESUME_KEY = "22222222-2222-4222-8222-222222222222/resumes/blob.pdf";

    private InMemoryStorageService storage;

    @BeforeEach
    void setUp() {
        storage = new InMemoryStorageService();
    }

    @Test
    void everyObjectThePortAcceptedComesBackFromTheListing() {
        storage.put(KNOWLEDGE_KEY, bytes("knowledge"), "application/pdf");
        storage.put(RESUME_KEY, bytes("resume"), "application/pdf");

        List<StoredObject> listed = storage.list();

        assertThat(listed).extracting(StoredObject::key)
                .containsExactlyInAnyOrder(KNOWLEDGE_KEY, RESUME_KEY);
        assertThat(listed).allSatisfy(object -> assertThat(object.bytes())
                .isEqualTo(object.key().equals(KNOWLEDGE_KEY) ? 9L : 6L));
    }

    @Test
    void anEmptyBucketAnswersWithNothingRatherThanWithANull() {
        // A sweep that reads null as "empty" reclaims nothing and reports a clean bucket; the
        // difference between the two is the difference between a night's work and a lie.
        assertThat(storage.list()).isEmpty();
    }

    @Test
    void anObjectSeededBehindThePortsBackDoorIsListedAsTooYoungToReclaim() {
        // The integration tests put bytes straight into the map, so the store can hold an object it
        // cannot date. Undated has to fail toward keeping the file: a zero or a null stamp would make
        // every seeded object look older than any window and hand a sweep a delete it should refuse.
        storage.store.put(KNOWLEDGE_KEY, bytes("seeded"));

        OffsetDateTime before = OffsetDateTime.now();
        StoredObject listed = storage.list().get(0);

        assertThat(listed.key()).isEqualTo(KNOWLEDGE_KEY);
        assertThat(listed.bytes()).isEqualTo(6L);
        assertThat(listed.lastModified()).isAfterOrEqualTo(before);
    }

    @Test
    void theMomentAnObjectLandedIsTheMomentTheListingReports() {
        // 48.2's window is measured against this stamp, so the knob a test turns has to be the thing
        // the sweep reads -- not a field the listing ignores while still passing its own cases.
        OffsetDateTime landed = OffsetDateTime.now().minusDays(400);
        storage.store.put(KNOWLEDGE_KEY, bytes("old"));
        storage.storedAt.put(KNOWLEDGE_KEY, landed);

        assertThat(storage.list()).containsExactly(new StoredObject(KNOWLEDGE_KEY, landed, 3L));
    }

    @Test
    void aReclaimedObjectLeavesTheListingAndItsStampWithIt() {
        storage.put(KNOWLEDGE_KEY, bytes("knowledge"), "application/pdf");
        storage.delete(KNOWLEDGE_KEY);

        // The stamp goes with the object, or a key re-used under the same name would be listed at its
        // previous age and reclaimed the moment it landed.
        assertThat(storage.list()).isEmpty();
        assertThat(storage.storedAt).isEmpty();

        storage.put(KNOWLEDGE_KEY, bytes("again"), "application/pdf");
        assertThat(storage.list().get(0).lastModified()).isAfterOrEqualTo(OffsetDateTime.now().minusSeconds(5));
    }

    @Test
    void aStoreThatRefusesMidwalkRefusesTheWholeListing() throws IOException {
        int deadPort;
        try (ServerSocket socket = new ServerSocket(0)) {
            deadPort = socket.getLocalPort();
        }

        assertThatThrownBy(minioAt("http://127.0.0.1:" + deadPort)::list)
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.code()).isEqualTo(ApiErrorCode.STORAGE_READ_FAILED));
    }

    /** The real adapter, pointed at a port nothing answers: the only failure a laptop can cause MinIO. */
    private static MinioStorageService minioAt(String endpoint) {
        AppProperties props = new AppProperties();
        props.getStorage().setEndpoint(endpoint);
        props.getStorage().setAccessKey("access");
        props.getStorage().setSecretKey("secret");
        props.getStorage().setBucket("careeros");
        return new MinioStorageService(props);
    }

    private static byte[] bytes(String text) {
        return text.getBytes(StandardCharsets.UTF_8);
    }
}
