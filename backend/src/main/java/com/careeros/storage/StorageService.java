package com.careeros.storage;

import java.time.Duration;

/** Object storage port. Files live in a private bucket; reads go through presigned URLs only. */
public interface StorageService {

    void put(String key, byte[] content, String contentType);

    String getPresignedUrl(String key, Duration ttl);

    void delete(String key);

    byte[] getBytes(String key);
}
