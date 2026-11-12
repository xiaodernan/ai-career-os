package com.careeros.queue;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.Range;
import org.springframework.data.redis.connection.RedisStreamCommands.XAddOptions;
import org.springframework.data.redis.connection.stream.Consumer;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.PendingMessage;
import org.springframework.data.redis.connection.stream.PendingMessages;
import org.springframework.data.redis.connection.stream.ReadOffset;
import org.springframework.data.redis.connection.stream.RecordId;
import org.springframework.data.redis.connection.stream.StreamOffset;
import org.springframework.data.redis.connection.stream.StreamReadOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * The Redis Streams half of {@link JobStream}: the only file in the backend that spells a
 * stream command.
 *
 * <p>Space is bounded at the write, not by a sweep: every XADD carries {@code MAXLEN ~ N},
 * so a producer that outruns its consumers cannot grow the stream without limit, and the
 * approximate form lets Redis trim whole radix nodes instead of one entry per write. The
 * dead-letter stream is bounded the same way -- a poison job is evidence, not a leak.
 *
 * <p>Nothing here decides policy. It does not catch a Redis outage: the caller that owns the
 * failure boundary ({@link JobQueue} for a producer, {@link JobWorker} for a tick) decides
 * what an unreachable server means, because those two answers are deliberately different.
 */
@Component
public class RedisJobStream implements JobStream {

    /** The one stream every backend job rides; bump the version when a payload shape changes. */
    public static final String STREAM = "careeros:v1:jobs";

    /** One group for the whole backend fleet: N replicas share it, so a job is handed to one. */
    public static final String GROUP = "backend";

    public static final String DEAD_STREAM = "careeros:v1:jobs:dlq";

    private final StringRedisTemplate redis;
    private final long maxLen;

    public RedisJobStream(StringRedisTemplate redis,
                          @org.springframework.beans.factory.annotation.Value("${careeros.queue.max-len:10000}") long maxLen) {
        this.redis = redis;
        this.maxLen = Math.max(1, maxLen);
    }

    @Override
    public void ensureGroup() {
        try {
            redis.opsForStream().createGroup(STREAM, ReadOffset.from("0"), GROUP);
        } catch (RuntimeException e) {
            // XGROUP CREATE on an existing group answers BUSYGROUP. That is the steady state,
            // not a failure: every replica after the first one sees it on its first tick.
            if (String.valueOf(e.getMessage()).contains("BUSYGROUP")) {
                return;
            }
            throw e;
        }
    }

    @Override
    public String add(Map<String, String> fields) {
        RecordId id = redis.opsForStream()
                .add(MapRecord.create(STREAM, fields), XAddOptions.maxlen(maxLen).approximateTrimming(true));
        return id == null ? "" : id.getValue();
    }

    @Override
    public String addDead(Map<String, String> fields) {
        RecordId id = redis.opsForStream()
                .add(MapRecord.create(DEAD_STREAM, fields), XAddOptions.maxlen(maxLen).approximateTrimming(true));
        return id == null ? "" : id.getValue();
    }

    @Override
    public List<Entry> read(String consumer, int count) {
        List<MapRecord<String, Object, Object>> records = redis.opsForStream().read(
                Consumer.from(GROUP, consumer),
                StreamReadOptions.empty().count(count),
                StreamOffset.create(STREAM, ReadOffset.lastConsumed()));
        return entries(records);
    }

    @Override
    public List<Pending> pending(int count) {
        PendingMessages messages = redis.opsForStream().pending(STREAM, GROUP, Range.unbounded(), count);
        List<Pending> out = new ArrayList<>();
        if (messages == null) {
            return out;
        }
        for (PendingMessage message : messages) {
            out.add(new Pending(message.getIdAsString(), message.getConsumerName(),
                    message.getElapsedTimeSinceLastDelivery(), message.getTotalDeliveryCount()));
        }
        return out;
    }

    @Override
    public List<Entry> claim(String consumer, Duration minIdle, List<String> ids) {
        if (ids.isEmpty()) {
            return List.of();
        }
        RecordId[] recordIds = ids.stream().map(RecordId::of).toArray(RecordId[]::new);
        return entries(redis.opsForStream().claim(STREAM, GROUP, consumer, minIdle, recordIds));
    }

    @Override
    public void ack(String id) {
        redis.opsForStream().acknowledge(STREAM, GROUP, id);
    }

    private static List<Entry> entries(List<MapRecord<String, Object, Object>> records) {
        List<Entry> out = new ArrayList<>();
        if (records == null) {
            return out;
        }
        for (MapRecord<String, Object, Object> record : records) {
            Map<String, String> fields = new java.util.LinkedHashMap<>();
            record.getValue().forEach((key, value) -> fields.put(String.valueOf(key), String.valueOf(value)));
            out.add(new Entry(record.getId().getValue(), fields));
        }
        return out;
    }
}