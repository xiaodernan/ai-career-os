package com.careeros.storage;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;

/** Object storage port. Files live in a private bucket; reads go through presigned URLs only. */
public interface StorageService {

    void put(String key, byte[] content, String contentType);

    String getPresignedUrl(String key, Duration ttl);

    void delete(String key);

    byte[] getBytes(String key);

    /**
     * Every object the bucket holds, keyed and timed (48.1).
     *
     * <p>The contract is whole-or-nothing, and that is the whole point of the method: a listing that
     * came back short would let a sweep read an object the first page never reached as garbage and
     * delete it. So a store that cannot answer every page throws instead of answering, and the caller
     * that catches the throw reclaims nothing. {@link #available()} is deliberately not a guard --
     * it asks whether one round trip succeeds, which says nothing about the pages after it.
     *
     * <p>The result is a snapshot, not a live view: an object uploaded while this runs may or may
     * not appear. A caller that acts on the answer has to treat a missing key as "the store did not
     * show it to me", never as "no row can ever name it".
     */
    List<StoredObject> list();

    /**
     * Whether the store answers at all. A probe for the health line (39.1), not a request:
     * an unreachable store must be reported as unreachable, not thrown as a failed upload.
     */
    boolean available();

    /**
     * One object as the store describes it: the name a row would hold to point at it, when the store
     * last wrote it, and how many bytes are under it. {@code lastModified} is what a reclaim window
     * is measured against, so a store that cannot say when an object landed reports the moment this
     * listing read it rather than a silent zero -- the sweep then sees an object too young to burn,
     * which is the safe direction for a missing timestamp to fail in.
     */
    record StoredObject(String key, OffsetDateTime lastModified, long bytes) {
    }
}
