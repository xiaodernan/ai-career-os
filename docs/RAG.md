# RAG design

The retrieval-augmented core that grounds every AI feature (match, tailor, cover
letter, interview, copilot) in the user's own evidence. Implemented in
`ai-service/app/rag/` and described in PRD §5.

Everything is **scoped to a single `user_id`**: each channel query and the final
citations carry the caller's id, so one user's chunks never surface in another
user's prompt (see [SECURITY.md](SECURITY.md)).

## Pipeline

`rag/pipeline.retrieve()` runs, in order:

```
understand → hybrid retrieve → RRF fuse → rerank → compress → cite
```

1. **Understand** (`rag/rewrite.py::understand`) — one LLM call turns the raw
   query into `rewritten`, `expansions`, `keywords`, `intent` and optional
   metadata `filters.kinds`. The rewrite + expansions drive the embedding
   queries; the keywords drive the lexical channels.

2. **Hybrid retrieval** (`rag/store.py`) — several recall channels run in
   parallel and each returns an independent ranked list:
   - `vector_search` — pgvector ANN over the embeddings, one list per rewritten
     / expansion vector (top 25 each).
   - `keyword_search` — lexical (tsvector-style) match on rewritten text +
     keywords (top 25).
   - `trigram_search` — fuzzy trigram match to catch near-miss spellings (top 10).
   All channels accept `kinds` and optional `document_ids` filters.

   The keyword channel is bounded: `KEYWORD_FANOUT` (`rag/pipeline.py`) caps the phrases
   at the rewritten query plus four keywords, because each phrase is its own round trip.
   One phrase per call, never one concatenation — `plainto_tsquery` ANDs every term it is
   given, and a CJK run without spaces collapses to a single tsvector lexeme, so one
   unmatchable term would veto the whole channel. RRF supplies the OR across the phrases.

   **The `kinds` filter is a guess, and a guess that misses is dropped.** A caller's
   `kinds` is a request and is never second-guessed. The rewrite step's `filters.kinds` is
   a guess, and a guess matching nothing empties retrieval silently — which is how it
   survived: asked "what backend frameworks does the candidate know?", a real provider
   answered `kinds: ["project"]` for a user whose only source was a resume, and 13 of 15
   golden cases came back with no evidence at all. The pipeline retries once without the
   guess and traces the recovery as `kinds_filter_dropped`. An empty result is never more
   useful than a broader one.

3. **RRF fusion** (`store.rrf_merge`) — Reciprocal Rank Fusion merges the
   per-channel lists by chunk id (no score scale mismatch). Covered by
   `tests/test_core_modules.py::test_rrf_*`.

4. **Rerank** (`rag/rerank.py::rerank`) — `RERANK_MODE=llm` re-orders the fused
   candidates down to `top_k` with an LLM relevance pass (`none` skips it).

5. **Compress** (`rag/compress.py::compress`) — keeps only the sentences that
   overlap the query intent, with a floor so very relevant-but-terse chunks
   survive. Tested in `test_compress_*`.

6. **Cite** — each surviving chunk becomes an evidence record with `ref`,
   `chunk_id`, `document_id`, `doc_title`, `source_kind`, `section`, a 600-char
   `quote` and a rounded `score`. `context_block` (from `core.ai.evidence_block`)
   is the text actually injected into the prompt, and the same evidence list is
   returned to the UI so every AI answer can show its sources.

## Chunk model & kinds

Sources are stored as chunks with a `source_kind`. The features request specific
kinds per task — e.g. cover-letter generation retrieves `["resume", "project",
"goal"]`. New kinds are added at ingestion time (`app/ingestion/`), which parses
uploaded resumes / documents and text notes into the vector store.

## Observability & streaming

Each stage emits a trace (`db.observability.trace`) under the run's `run_id`, and
when driven by a streaming task it publishes `status` steps
(`understanding_query → hybrid_retrieval → reranking`) over the task bus so the
frontend `ProcessingSteps` / SSE surface shows live progress.

## Providers

Embeddings come from the provider registry (`providers.registry.get_embeddings`):
`openai` (default), `ollama` (local), or `hash` — a deterministic offline stub
for tests only; retrieval quality with `hash` is intentionally limited.
