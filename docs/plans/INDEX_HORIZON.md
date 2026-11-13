# Index horizon — measured, not guessed

A short inventory of the btrees the live database gains because a plan was
measured, not because a list looked complete.

## Shipped
- **V23** `__credential_token_expiry_indexes` — expiry-minded token sweeps.
- **V36** `__search_lookup_indexes` — global search's recent-first scans.
- **V38** `__ai_usage_events_run_id` — `run_id`, the child side of the `ai_usage_events` ↔ `agent_runs` FK. The read pattern is the AI Activity page and the nightly rollup: `WHERE run_id = :id`. Measured on this install against the 161-row local table: `Seq Scan on ai_usage_events` with `Rows Removed by Filter: 157`.

## Audit result (this round, measured with `\d` + EXPLAIN ANALYZE)

The next candidates all **already** ship an index today — `agent_traces(run_id, seq)`, `messages(conversation_id, created_at)`, `document_chunks(document_id, ordinal)`.
The `documents(user_id)`, `agent_runs(user_id, started_at)` and `user_memories(user_id, kind)` indexes are also already present.
The one real gap the audit found was `ai_usage_events.run_id`; V38 closes it.

## Verification
- `FleetWiringIT` re-ran against a Flyway-rebuilt IT database including V38: 2/2 green.
- The EXPLAIN evidence on the local table: `Limit (actual time=3.265..3.374 rows=3)` with `Rows Removed by Filter: 157` at `Planning Time: 24.961 ms` baseline.
