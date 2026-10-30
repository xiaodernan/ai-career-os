package com.careeros.storage;

import java.time.Duration;

/** Object storage port. Files live in a private bucket; reads go through presigned URLs only. */
public interface StorageService {

    void put(String key, byte[] content, String contentType);

    String getPresignedUrl(String key, Duration ttl);

    void delete(String key);

    byte[] getBytes(String key);

    /**
     * Whether the store answers at all. A probe for the health line (39.1), not a request:
     * an unreachable store must be reported as unreachable, not thrown as a failed upload.
     */
    boolean available();
}
