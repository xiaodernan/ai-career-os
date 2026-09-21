package com.careeros.support;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.storage.StorageService;
import java.time.Duration;
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

        @Override
        public void put(String key, byte[] content, String contentType) {
            store.put(key, content.clone());
        }

        @Override
        public String getPresignedUrl(String key, Duration ttl) {
            return "http://inmemory.local/" + key;
        }

        @Override
        public void delete(String key) {
            store.remove(key);
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
