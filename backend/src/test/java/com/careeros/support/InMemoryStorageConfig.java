package com.careeros.support;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.storage.StorageService;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * In-memory StorageService used by integration tests (MinIO is disabled via
 * app.storage.enabled=false). Backs uploads with a byte map so the internal file endpoint and the
 * upload happy/failure paths can be exercised without a real object store.
 */
@Configuration
public class InMemoryStorageConfig {

    @Bean
    public StorageService inMemoryStorageService() {
        return new InMemoryStorageService();
    }

    public static class InMemoryStorageService implements StorageService {

        public final Map<String, byte[]> store = new ConcurrentHashMap<>();

        /**
         * When each object landed, which is what a reclaim window measures. The map is public and
         * writable because the window is the thing under test: a pass that has to prove it spares a
         * young object needs to make one, and `now` in a test is not a knob.
         *
         * <p>A key can be in {@link #store} with no entry here -- the ITs seed bytes by writing the
         * map directly. Such an object is listed as modified right now, which is the direction that
         * keeps a sweep from reclaiming an object it cannot date.
         */
        public final Map<String, OffsetDateTime> storedAt = new ConcurrentHashMap<>();

        @Override
        public void put(String key, byte[] content, String contentType) {
            store.put(key, content.clone());
            storedAt.put(key, OffsetDateTime.now());
        }

        @Override
        public String getPresignedUrl(String key, Duration ttl) {
            return "http://inmemory.local/" + key;
        }

        @Override
        public void delete(String key) {
            store.remove(key);
            storedAt.remove(key);
        }

        /**
         * The whole map at once, in key order, with nothing filtered: the port promises a listing
         * that covers the bucket, and a double that dropped a prefix or a size to make a test read
         * better is a double that lets a sweep's arithmetic pass on a shape no store answers.
         */
        @Override
        public List<StoredObject> list() {
            return store.entrySet().stream()
                    .sorted(Comparator.comparing(Map.Entry::getKey))
                    .map(entry -> new StoredObject(entry.getKey(),
                            storedAt.getOrDefault(entry.getKey(), OffsetDateTime.now()),
                            (long) entry.getValue().length))
                    .toList();
        }

        /** The in-memory store answers by construction; there is no socket to be down. */
        @Override
        public boolean available() {
            return true;
        }

        @Override
        public byte[] getBytes(String key) {
            byte[] bytes = store.get(key);
            if (bytes == null) {
                throw new ApiException(ApiErrorCode.DOCUMENT_NOT_FOUND, "Object not found: " + key);
            }
            return bytes;
        }
    }
}
