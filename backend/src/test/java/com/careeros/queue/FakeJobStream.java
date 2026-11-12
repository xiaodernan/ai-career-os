package com.careeros.queue;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * An in-memory Redis Streams group: the same bookkeeping the server does, without a socket.
 *
 * <p>It keeps the three facts the queue's policy actually reads -- a per-group last-delivered
 * cursor, a pending-entries list with a delivery count and an idle time per entry, and an
 * explicit ack -- so a test can crash a consumer by simply never acking and watch a sibling
 * reclaim the work. What it cannot contradict is the server's own re-check of idle time inside
 * XCLAIM or the trimming of a bounded stream; {@code JobQueueIT} drives the real thing for those.
 *
 * <p>The command counters are the point of the fake for the opt-in contract: "disabled sends no
 * Redis command" is a claim about calls, and a fake that counts them is what makes it checkable.
 */
final class FakeJobStream implements JobStream {

    private static final class Pel {
        String consumer;
        long deliveredAt;
        long deliveries;

        Pel(String consumer, long deliveredAt, long deliveries) {
            this.consumer = consumer;
            this.deliveredAt = deliveredAt;
            this.deliveries = deliveries;
        }
    }

    final Map<String, Map<String, String>> entries = new LinkedHashMap<>();
    final Map<String, Pel> pel = new LinkedHashMap<>();
    final List<Map<String, String>> dead = new ArrayList<>();

    long now = 1_000_000L;
    private long seq;
    private int cursor;
    boolean groupCreated;

    RuntimeException addFailure;
    RuntimeException readFailure;
    RuntimeException pendingFailure;
    RuntimeException claimFailure;
    RuntimeException ackFailure;
    RuntimeException deadFailure;
    RuntimeException groupFailure;

    int adds;
    int reads;
    int pendings;
    int claims;
    int acks;
    int groups;

    int commands() {
        return adds + reads + pendings + claims + acks + groups;
    }

    /** Zeroes the call counters, so a test can set work up and then measure only its own tick. */
    void resetCounters() {
        adds = reads = pendings = claims = acks = groups = 0;
    }

    void advance(Duration by) {
        now += by.toMillis();
    }

    /** Puts an entry straight into a consumer's PEL, the state a crashed replica leaves behind. */
    String strand(String consumer, Map<String, String> fields, long deliveries) {
        String id = append(fields);
        pel.put(id, new Pel(consumer, now, deliveries));
        cursor = entries.size();
        return id;
    }

    private String append(Map<String, String> fields) {
        String id = now + "-" + (seq++);
        entries.put(id, new LinkedHashMap<>(fields));
        return id;
    }

    @Override
    public void ensureGroup() {
        groups++;
        if (groupFailure != null) {
            throw groupFailure;
        }
        groupCreated = true;
    }

    @Override
    public String add(Map<String, String> fields) {
        adds++;
        if (addFailure != null) {
            throw addFailure;
        }
        return append(fields);
    }

    @Override
    public String addDead(Map<String, String> fields) {
        adds++;
        if (deadFailure != null) {
            throw deadFailure;
        }
        dead.add(new LinkedHashMap<>(fields));
        // A separate stream, not another entry in this one: the first draft appended here and
        // the worker then read its own dead-letter record back as fresh work.
        return now + "-dead-" + (seq++);
    }

    @Override
    public List<Entry> read(String consumer, int count) {
        reads++;
        if (readFailure != null) {
            throw readFailure;
        }
        List<Entry> out = new ArrayList<>();
        List<String> ids = new ArrayList<>(entries.keySet());
        while (cursor < ids.size() && out.size() < count) {
            String id = ids.get(cursor++);
            pel.put(id, new Pel(consumer, now, 1));
            out.add(new Entry(id, entries.get(id)));
        }
        return out;
    }

    @Override
    public List<Pending> pending(int count) {
        pendings++;
        if (pendingFailure != null) {
            throw pendingFailure;
        }
        List<Pending> out = new ArrayList<>();
        for (Map.Entry<String, Pel> row : pel.entrySet()) {
            if (out.size() >= count) {
                break;
            }
            Pel value = row.getValue();
            out.add(new Pending(row.getKey(), value.consumer,
                    Duration.ofMillis(now - value.deliveredAt), value.deliveries));
        }
        return out;
    }

    @Override
    public List<Entry> claim(String consumer, Duration minIdle, List<String> ids) {
        claims++;
        if (claimFailure != null) {
            throw claimFailure;
        }
        List<Entry> out = new ArrayList<>();
        for (String id : ids) {
            Pel row = pel.get(id);
            // The server re-checks the idle time inside XCLAIM; a live consumer keeps its work.
            if (row == null || now - row.deliveredAt < minIdle.toMillis()) {
                continue;
            }
            row.consumer = consumer;
            row.deliveredAt = now;
            row.deliveries++;
            out.add(new Entry(id, entries.get(id)));
        }
        return out;
    }

    @Override
    public void ack(String id) {
        acks++;
        if (ackFailure != null) {
            throw ackFailure;
        }
        pel.remove(id);
    }
}